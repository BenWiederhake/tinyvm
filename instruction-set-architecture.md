# Instruction set architecture

## Meta

- Havard architecture (separate instruction memory and data memory). The reason is to make self-modifying programs impossible.
- Every pointer is 16 bit. This implies relatively low memory limits, which is basically the point of this VM.
- Every instruction is 16 bit. This simplifies parsing and code generation.
- By design, an all-zero and an all-ones value is an illegal instruction. This should make is slightly easier to detect programming errors.
- There are 64K addressable 16-bit words. (That is 128K bytes.) Alternatively, you could say that our bytes have 16 bits, but let's stick to the terms "byte = 8 bit" and "word = 16 bit".
- There are 16 registers, all of which are general-purpose.
- There is no build-in support for stack frames or anything. I want this to be a seriously limited VM with only basic algorithms, and if you want fancy things like recursion or local variables, then you'll have to pay for it by yourself.
- There is special support for ease of use (return, cpuid, etc.)
- Data is stored in big-endian order. E.g., if the first byte in data memory is 0x12, and the second byte is 0x34, then loading the first word into a register results in that register having value 0x1234.
- The program counter is not explicitly readable, and usually increments by one (with overflow) after each instruction (except for illegal, reserved, return, jump, and branch instructions).
- There is no concept such as hardware exceptions or interrupts.

## General instruction pattern

All instructions consist of exactly 16 bits. They are arranged in a prefix-tree pattern, so that reading from the most-significant bits of the first byte down to the least-significant bits of the second byte progressively specifies more and more about the instruction.

There are three types of valid instructions:
1. The first 4 bits identifies the instruction command, and the remaining 12 bits indicate data (usually 4 bits to identify a register, and 8 bits to encode an immediate value).
2. The first 8 bits identify the instruction command, and the remaining 8 bits idicate data (4+4 bits to identify two registers).
3. All bits are part of the instruction command, and the instruction carries no data.

## Instruction set layout

Case distinction over the first (most significant) four bits of the first byte:

- 0000:
    * 0000: illegal instruction
    * 0001-1111: reserved (see note)
- 0001:
    * 0000: Special argument-less instructions (Return, CPUID, Debug-dump, Time)
        * other instructions starting with 00010000 are reserved (see note)
    * 0001-1111: reserved (see note)
- 0010:
    * 0000: Store word data
    * 0001: Load word data
    * 0010: Load word instruction
    * 0011-1111: reserved (see note)
- 0011: Load immediate low (sign-extended)
- 0100: Load immediate high (only high byte)
- 0101:
    * 0000-1001: reserved (see note)
    * 1010: unary not
    * 1011: unary popcnt
    * 1100: unary clz
    * 1101: unary ctz
    * 1110: unary rnd
    * 1111: unary mov
- 0110: Basic binary (+, -, \*, \*h,   \/u, \/s, %u, %s,   &, |, ^, <<,  >>u, >>s, \*\*s, root)
- 0111: reserved (see note)
- 1000: Compare
- 1001: Branch
- 1010: Jump by immediate
- 1011: Jump to register
- 1100: reserved (see note)
- 1101: reserved (see note)
- 1110: reserved (see note)
- 1111:
    * 0000-1110: reserved (see note)
    * 1111: illegal instruction

Notes:
- "illegal instruction" means: Any attempt to execute this instruction should halt the machine, and result in an error.
- "reseved" means: For now these instructions should be treated as illegal instructions. Future versions of the VM, possibly when some flags are enabled, are allowed to behave differently. Implementors should make an effort that any deviation from treating reserved instructions as illegal instructions can be safely and easily deduced from the CPUID instruction.

## Specific instruction documentation

### `0x102A`: Return

`0b0001 0000 0010 1010`, type 3 (instruction carries no data)

This reads register 0 – or, in some sense, reads all registers and all memory.

Halts the machine. There is no execution  The content of register 0 is considered to be the primary return value. Depending on the use case, other registers and/or memory may also be considered to be return value.

Example: The instruction is `0b0001 0000 0010 1010`, and register 0 contains the value 0x0042. Then this instruction will halt the machine, and present the value 0x0042 as the main result.

### `0x102B`: CPUID

`0b0001 0000 0010 1011`, type 3 (instruction carries no data)

This reads register 0, and writes to registers 0, 1, 2, and 3.

The new value of these registers should be 0x0000 by default, unless the VM wants to indicate that a particular feature (usually in the form of specific instructions) is available.

Known feature flags depending on the content of register 0 before calling this instruction:
- Register 0 was 0x0000, bit 0 (mask 0x8000) of register 0: The VM attempts to be conformant to this specification, i.e. always 1.
- Register 0 was 0x0000, bit 1 (mask 0x4000) of register 0: The binary instructions for exponentiation and roots are supported.
- Other feature flags will be documented here.

Example: The instruction is `0b0001 0000 0010 1011`, and register 0 contains the value 0x0000. Then this instruction might, in a bare-bones and conforming VM, overwrite the register 0 with the value 0x8000, and registers 1, 2, and 3 each with the value 0x0000.

Example: The instruction is `0b0001 0000 0010 1011`, register 0 contains the value 0x0007. Then this instruction should, in any VM without exotic extensions, overwrite the registers 0, 1, 2, and 3 each with the value 0x0000.

### `0x102C`: Debug-dump

`0b0001 0000 0010 1100`, type 3 (instruction carries no data)

This reads no registers – or, in some sense, reads all registers and all memory.

Indicates to the VM that an observer may be interested in the current state of the machine. There is no directly observable side-effect. This may or may not pause the VM.

Example: The instruction is `0b0001 0000 0010 1100`. Then memory and registers remain unchanged, and the program counter is incremented as usual. However, the caller of the VM may or may not decide to halt and inspect the VM, potentially resuming it later.

### `0x102D`: Time

`0b0001 0000 0010 1101`, type 3 (instruction carries no data)

This writes to registers 0, 1, 2, and 3.

The new value of these registers is the amount of instructions that have been executed before this instruction, interpreted as a 64-bit number, with register 0 now carrying the most significant bits, and register 3 now carrying the least significant bits.

Example: The instruction is `0b0001 0000 0010 1101`, and before this instruction, 7 instructions have already been executed. Then the registers 0, 1, 2, and 3 now contain the values 0x0000, 0x0000, 0x0000, and 0x0007, respectively. Note that this does not depend on the program counter.

### `0x20xx`: Store word data

`0b0010 0000 AAAA VVVV`, type 2 (instruction carries two register indices)

This reads from registers 0bAAAA and 0bVVVV.

This instruction reads a value from register 0bVVVV, and writes it to the address stored in register 0bAAAA of data memory. Note that data memory is word-indexed, so the address 1 refers to bytes 2 and 3.

Example: The instruction is `0b0010 0000 0010 0101`, register 2 holds the value 0x1234, and register 5 holds the value 0x5678. Then this instruction will overwrite data memory at address 0x1234 with the value 0x5678.

### `0x21xx`: Load word data

`0b0010 0001 AAAA DDDD`, type 2 (instruction carries two register indices)

This reads from register 0bAAAA, and writes to register 0bDDDD.

This instruction reads a word of data memory at the address stored in register 0bAAAA. This word is written to the destination register 0bDDDD.

Example: The instruction is `0b0010 0001 0010 0101`, register 2 holds the value 0x1234, and data memory at address 0x1234 is 0x5678. Then this instruction will write the value 0x5678 into register 5.

### `0x22xx`: Load word instruction

`0b0010 0010 AAAA DDDD`, type 2 (instruction carries two register indices)

This reads from register 0bAAAA, and writes to register 0bDDDD.

This instruction reads a word of instruction memory at the address stored in register 0bAAAA. This word is written to the destination register 0bDDDD.

Example: The instruction is `0b0010 0010 0010 0101`, register 2 holds the value 0x1234, and instruction memory at address 0x1234 is 0x5678. Then this instruction will write the value 0x5678 into register 5.

Note that this instruction can be used to provide the program with a limited amount of read-only memory, at the expense of available space for program code.

### `0x3xxx`: Load immediate low (sign-extended)

`0b0011 RRRR SVVV VVVV`, type 1 (instruction carries one register index and an 8-bit value)

This writes to register 0bRRRR.

This instruction interprets the value `0bSVVVVVVV` as an 8-bit byte, sign-extends it to a 16-bit word (0bSSSSSSSSSVVVVVVV), and writes the result to register 0bRRRR.

Example: The instruction is `0b0011 0101 1000 1110`. Then this instruction will write the value 0xFF8E into register 5.

### `0x4xxx`: Load immediate high (only high byte)

`0b0100 RRRR VVVV VVVV`, type 1 (instruction carries one register index and an 8-bit value)

This reads from and writes to register 0bRRRR.

This instruction interprets the value `0bVVVVVVVV` as an 8-bit byte, and uses it to overwrite the most-significant byte of register 0bRRRR.

Example: The instruction is `0b0100 1010 0101 0110`, and register 10 contains the value 0x1234. Then this instruction will write the value 0x5634 into register 5.

Note that in combination with the "load immediate low" instruction, this provides a straight-forward way to load an arbitrary value into a register using only two instructions. Example: The two instructions `0x37CD 0x47AB` sets register 7 to the value 0xABCD.

### `0x5xxx`: Unary functions

`0b0101 FFFF SSSS DDDD`, several instructions of type 2 (instruction carries two register indices)

This reads from register 0bSSSS, and writes to register 0bDDDD.

This computes a simple mathematical function using only the value of the source register 0bSSSS, and writes it into the destination register 0bDDDD, where FFFF selects the desired unary function.

* If FFFF=1010, the computed function is "not" (bite-wise logical negation), e.g. not(0x1234) = 0xEDCB
* If FFFF=1011, the computed function is "popcnt" (population count), e.g. popcnt(0xFFFF) = 16, popcnt(0x0000) = 0
    * Note that there are no silly exceptions as there would be in x86.
* If FFFF=1100, the computed function is "clz" (count leading zeros), e.g. clz(0x8000) = 0, clz(0x0002) = 14
* If FFFF=1101, the computed function is "ctz" (count trailing zeros), e.g. ctz(0x8000) = 15, ctz(0x0002) = 1
* If FFFF=1110, the computed function is "rnd" (random number up to AND INCLUDING), e.g. rnd(5) = 3, rnd(5) = 5, rnd(5) = 0
    * Note that rnd must never result in a value larger than the argument, so rnd(5) must never generate 6 or even 0xFFFF.
* If FFFF=1111, the computed function is "mov" (move, identity function), e.g. mov(0x5678) = 0x5678
* Other values of FFFF indicate reserved functions, and should be treated as a reserved instructions.

Example: The instruction is `0b0101 1010 0101 0110`, and register 5 contains the value 0x1234. Then this instruction will write the value 0xEDCB into register 6, because not(0x1234) = 0xEDCB.

### `0x6xxx`: Basic binary functions

`0b0110 FFFF LLLL RRRR`, several instructions of type 2 (instruction carries two register indices)

This reads from registers 0bLLLL and 0bRRRR, and writes to register 0bRRRR.

This computes a simple mathematical function using only the values of the registers 0bLLLL and 0bRRRR, used as left-hand side and right-hand side operand respectively. The result is written into the register 0bRRRR, thus overwriting the formerly right-hand side value. The value of FFFF selects the desired binary function.

* If FFFF=0000, the computed function is "+" (overflowing addition), e.g. fn(0x1234, 0xABCD) = 0xBE01
    * Note that there is no need to distinguish signedness, as the results would always bit-identical.
* If FFFF=0001, the computed function is "-" (overflowing subtraction), e.g. fn(0xBE01, 0xABCD) = 0x1234, fn(0x0009, 0x0007) = 0xFFFE
    * Note that there is no need to distinguish signedness, as the results would always bit-identical.
* If FFFF=0010, the computed function is "*" (truncated multiplication, low word), e.g. fn(0x0005, 0x0007) = 0x0023, fn(0x1234, 0xABCD) = 0x4FA4
    * Note that there is no need to distinguish signedness, as the results would always bit-identical.
* If FFFF=0011, the computed function is "*h" (truncated multiplication, high word), e.g. fn(0x0005, 0x0007) = 0x0000, fn(0x1234, 0xABCD) = 0x0C37
    * Note that there is no need to distinguish signedness, as the results would always bit-identical.
* If FFFF=0100, the computed function is "/u" (unsigned division, rounded towards negative infitity), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0x0009
    * The result of dividing by zero is 0xFFFF, the highest unsigned value.
* If FFFF=0101, the computed function is "/s" (signed division, rounded towards negative infitity), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0xFFFA
    * The result of dividing by zero is 0x7FFF, the highest signed value.
* If FFFF=0110, the computed function is "%u" (unsigned modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x07F9
    * The result of modulo by zero is 0x0000.
* If FFFF=0111, the computed function is "%s" (signed modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x06D1
    * The result of modulo by zero is 0x0000.
* If FFFF=1000, the computed function is "&" (bitwise and), e.g. fn(0x5500, 0x5050) = 0x5000
* If FFFF=1001, the computed function is "|" (bitwise inclusive or), e.g. fn(0x5500, 0x5050) = 0x5550
* If FFFF=1010, the computed function is "^" (bitwise exclusive or), e.g. fn(0x5500, 0x5050) = 0x0550
* If FFFF=1011, the computed function is "<<" (bitshift left, filling the least-significant bits with zero), e.g. fn(0x1234, 0x0001) = 0x2468, fn(0xFFFF, 0x0010) = 0x0000
    * Note that there are no silly exceptions as there would be in x86.
* If FFFF=1100, the computed function is ">>u" (logical bitshift right, filling the most significant bits with zero), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0x0000
* If FFFF=1101, the computed function is ">>s" (arithmetic bitshift right, filling the most significant bits with the sign-bit), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0xFFFF
* Other values of FFFF indicate reserved functions, and should be treated as a reserved instructions, unless indicated by the corresponding feature flag.
    * If FFFF=1110, the computed function may be "\*\*s" (signed exponentiation according to IEEE754 double-precision arithmetic, then rounded to the nearest integer, clamped between 0x8000 (-32768) and 0x7FFF (+32767)), e.g. fn(0x0003, 0x0005) = 0x00F3, fn(0xFFFF, 0x0002) = 0x0001
        * If the result is positive or negative Infinity, it is clamped accordingly.
        * If the result is NaN (can this even happen?), the written value may be arbitrary.
    * If FFFF=1111, the computed function may be "n-th root" (signed root according to IEEE754 double-precision arithmetic, then rounded to the nearest integer), e.g. fn(0x0009, 0x0002) = 0x0003, fn(0x0900, 0x0002) = 0x0030, fn(0x00F3, 0x0005) = 0x0003, fn(0x0002, 0x0002) = 0x0001, fn(0x1234, 0x0000) = 0x0001
        * If the result is NaN, the written value may be arbitrary.

Example: The instruction is `0b0110 0010 0101 0110`, register 5 contains the value 0x0005, and register 6 contains the value 0x0007. Then this instruction will write the value 0x0023 into register 6, because 5 \* 7 = 35 = 0x0023.

### `0x8xxx`: Compare

`0b1000 LEGS AAAA BBBB`, several instructions of type 2 (instruction carries two register indices)

This reads from registers 0bAAAA and 0bBBBB, and writes to register 0bBBBB.

This compares the values in registers 0bAAAA and 0bBBBB, and writes 0x0000 (false) or 0x0001 (true) into register 0bBBBB. The bits L, E, G, and S are flags.

- By default, the result of the comparison is false, and the contents of the registers are interpreted as unsigned.
- If L=1 and the content of register 0bAAAA is *smaller* than the content of register 0bBBBB.
- If E=1 and the content of register 0bAAAA is *equal* to the content of register 0bBBBB.
- If G=1 and the content of register 0bAAAA is *greater* than the content of register 0bBBBB.
- If S=1, the contents of the registers are instead interpreted as signed.

Note that this implies a few interesting combinations:
- The combinations L=1, E=1, G=0 and L=0, E=1, G=1 effectively compare whether the values are less-or-equal, or greater-or-equal, respectively.
- The combination L=1, E=0, G=1 effectively checks whether values are non-equal.
- If all flags are set or no flags are set, this is effectively a "load immediate" instruction. This is a bit silly, but the ease of use and the relatively sparsely populated instruction space seems worth the trade-off.

Example: The instruction is `0b1000 1010 0011 0100`, register 3 contains the value 0x0005, and register 4 contains the value 0x0007. Then this instruction will write the value 0x0001 into register 4, because 5 is not equal 7.

### `0x9xxx`: Branch

`0b1001 RRRR SVVV VVVV`, type 1 (instruction carries one register index and an 8-bit value)

This reads from register 0bRRRR, and may affect the program counter.

If the content of register 0bRRRR are 0x0000, execution continues with no special effect to the program counter. If the content of register 0bRRRR is anything other than 0x0000, the program counter is changed in the following way:

- If S=0, the program counter is not incremented by 1 as usual, but rather incremented by 2 + 0b0VVVVVVV.
- If S=1, the program counter is not incremented by 1 as usual, but rather decremented by 1 + 0b0VVVVVVV.

Note that the program counter is allowed to overflow.

Note that this is somewhat similar to interpreting 0bSVVVVVVV as a signed 8-bit value and adding it to the program counter. The difference is that two special cases are removed, which is the conditional infinite loop (branching to the branch instruction itself), and a no-op (branching to the next instruction, which would have been executed anyway). The reason for this design choice is to slightly extend the range of a simple branch instruction.

If you need long conditional branches, consider using a jump by immediate (containing a 12-bit offset), or load immediate and jump to register to jump to an arbitrary 16-bit address.

Example: The program counter is 0x1234, the instruction at that address is `0b1001 0011 1000 0000`, and register 3 contains the value 0x0001. Because 0x0001 is considered true, the program counter is then updated to 0x1233, i.e. the instruction before the branch.

Example: The instruction is `0b1001 0101 1000 0000`, and register 5 contains the value 0x0000. Because 0x0000 is considered false, the program counter is incremented as normal.

### `0xAxxx`: Jump by immediate

`0b1010 SVVV VVVV VVVV`, type 1 (instruction carries a 12-bit value)

This reads and writes no registers, but will affect the program counter.

The program counter is changed in the following way:

- If S=0, the program counter is not incremented by 1 as usual, but rather incremented by 2 + 0b0000 0VVV VVVV VVVV.
- If S=1, the program counter is not incremented by 1 as usual, but rather decremented by 1 + 0b0000 0VVV VVVV VVVV.

Note that the program counter is allowed to overflow.

Note that this is somewhat similar to interpreting 0bSVVVVVVVVVVV as a signed 12-bit value and adding it to the program counter. The difference is that two special cases are removed, which is the infinite loop (jumping to the jump instruction itself), and a no-op (jumping to the next instruction, which would have been executed anyway). The reason for this design choice is to slightly extend the range of a simple jump instruction.

If you need long jumps, consider a load immediate and jump to register.

Example: The program counter is 0x5000, the instruction at that address is `0b1010 0001 0010 0011`. Then the program counter is updated to 0x5000 + 2 + 0x0123 = 0x5125.

Example: The program counter is 0x1234, the instruction at that address is `0b1010 1000 0000 0000`. Then the program counter is updated to 0x1233, i.e. the instruction before the jump.

### `0xBxxx`: Jump to register

`0b1011 RRRR SVVV VVVV`, type 1 (instruction carries one register index and an 8-bit value)

This reads from register 0bRRRR, and will affect the program counter.

Instead of incrementing the program counter by one, it is instead set to a new value independent of the old value. The new value is computed as the content of register 0bRRRR plus the value 0bSSSS SSSS SVVV VVVV, i.e. the second instruction byte is interpreted as a sign-extended offset.

Note that the program counter is allowed to overflow.

Note that this means that any jump takes at most three instructions: two instructions to load the value into an unused register, and one instruction for this jump.

Example: The instruction is `0b1011 0111 0011 0100`, and register 7 contains the value 0x1200. Then the program counter is updated to 0x1234.

Example: The instruction is `0b1011 0111 1111 1111`, and register 7 contains the value 0x1234. Then the program counter is updated to 0x1233.
