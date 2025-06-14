# Assembly language

## Meta

- Very closely modeled to the ISA, unsurprisingly.
- Since the program counter will silently (and successfully) wrap, so will code generated by the assembler. That means you could start writing code at 0xFFF5 and after a bunch of words end up at 0003. That's a feature.
- The assembler refuses to let you overwrite previously-generated code, i.e. there is no silent data loss.
- Special assembler [directives](#directives) probably work very differently than in "usual" assembly.
- The assembly language uses the concept of labels, as most languages do. Forward-references are allowed unless otherwise noted, and completeness is checked at the end.
- Note that there are several instructions that take two registers as arguments, and some modify the LHS (following various other assembly languages), some modify the RHS (following my intuition of going from left to right). This is unfortunate. In order to avoid unintentional errors, instructions that "write" to the LHS require a comma (e.g. `lw r3, r6` and `sw r6, r3`), and instructions that modify the RHS forbid commas (e.g. `add r1 r2`).

## Instructions by ISA

Notation:
* `reg_foo`: A register is expected, like `r0`, `r1`, …, `r15`. The purpose is `foo`.
* `imm_bar`: An immediate value is expected, like `0`, `42`, `-0x1234`. The purpose is `bar`.
* `lab_quux`: A label name is expected, like `_hello`, `_a`, `_must_start_with_an_underscore`. The purpose is `quux`.
* `[ reg_foo ]`: Square brackets indicate that the argument is optional.
* `( imm_bar | _lab_quux )`: Round parenthesis with pipes in-between indicate that there are multiple options, and exactly one must be given.

<!-- CAUTION WHEN EDITING! Markdown does linebreaks by two trailing spaces. This is disgusting. -->

Instructions by prefix:
- 0000:
    * 0000: illegal instruction, cannot be generated
    * 0001-1111: reserved, cannot be generated
- 0001:
    * 0000: `yield`, `cpuid`, `debug`, `time`
    * 0001-1111: reserved, cannot be generated
- 0010:
    * 0000: `sw reg_addr, reg_value` (Store word data)
    * 0001: `lw reg_dest, ( reg_addr | imm_value )` (Load word data)
        * Note that `lw reg_dest imm_value` is a shorthand, and accepts `-0x8000 <= imm_value <= 0xFFFF`.
    * 0010: `lwi reg_dest, reg_addr` (Load word instruction)
    * 0011-1111: reserved, cannot be generated
- 0011: `lw reg_dest, imm_value` (Load immediate low, sign-extended)
    * Note that for `-0x80 <= imm_value <= 0x7F` this results in only one instruction.
    * For convenience and future compatibility, the same guarantee holds for `0xFF80 <= imm_value <= 0xFFFF`.
    * If `imm_value` is outside this range, theo two instructions `lw reg_dest, imm_low_bits; lhi reg_dest, imm_high_bits` are generated instead. See the section on [pseudo-instructions](#pseudo-instructions) for more instances of such dynamic behavior.
- 0100: `lhi reg_dest, imm_value` (Load immediate high, only high byte)
    * Auto-detects which byte contains the desired value: `0x00 <= imm_value <= 0xFF` will use the low byte,
      `(imm_value & 0xFF == 0) && (0x0000 <= imm_value <= 0xFF00)` will use the high byte.
- 0101:
    * 0000-1001: reserved, cannot be generated
    * 1000: `decr reg_dest [, reg_src]` (unary decr)
        * If no `reg_src` is supplies, it is assumed to be identical to `reg_dest`. This also holds for all other unary operations.
    * 1001: `incr reg_dest [, reg_src]` (unary incr)
    * 1010: `not reg_dest [, reg_src]` (unary not)
    * 1011: `popcnt reg_dest [, reg_src]` (unary popcnt)
    * 1100: `clz reg_dest [, reg_src]` (unary clz)
    * 1101: `ctz reg_dest [, reg_src]` (unary ctz)
    * 1110: `rnd reg_dest [, reg_src]` (unary rnd)
    * 1111: `mov reg_dest, reg_src` (unary mov)
        * Note that single-arg movs and movs with the same source and destination register are forbidden in the assembly language, as they are noop instructions.
          If you really insist on inserting a noop, you can still write `nop` (see [pseudo-instructions](#pseudo-instructions)) or `.data 5F00`.
- 0110: Basic binary (+, -, \*, \*h,   \/u, \/s, %u, %s,   &, |, ^, <<,  >>u, >>s, \*\*s, root)
    * 0000: `add reg_lhs reg_rhs_dest` (+)
        * As per the ISA, the result is written into the right-hand side operand, i.e. `reg_rhs_dest`. This also holds for all other unary operations.
    * 0001: `sub reg_lhs reg_rhs_dest` (-)
    * 0010: `mul reg_lhs reg_rhs_dest` (\*)
    * 0011: `mulh reg_lhs reg_rhs_dest` (\*h)
    * 0100: `divu reg_lhs reg_rhs_dest` (\/u)
    * 0101: `divs reg_lhs reg_rhs_dest` (\/s)
    * 0110: `modu reg_lhs reg_rhs_dest` (%u)
    * 0111: `mods reg_lhs reg_rhs_dest` (%s)
    * 1000: `and reg_lhs reg_rhs_dest` (&)
    * 1001: `or reg_lhs reg_rhs_dest` (|)
    * 1010: `xor reg_lhs reg_rhs_dest` (^)
    * 1011: `sl reg_lhs reg_rhs_dest` (<<)
    * 1100: `srl reg_lhs reg_rhs_dest` (>>u)
    * 1101: `srl reg_lhs reg_rhs_dest` (>>s)
    * 1110: `exp reg_lhs reg_rhs_dest` (\*\*s)
        * NOT IMPLEMENTED, the VM also doesn't support it (yet?)
    * 1111: `root reg_lhs reg_rhs_dest` (root)
        * NOT IMPLEMENTED, the VM also doesn't support it (yet?)
- 0111: reserved, cannot be generated
- 1000: Compare
    * 0000: cannot be generated (same as `lw reg_rhs_dest 0`)
    * 0001: cannot be generated (same as `lw reg_rhs_dest 0`)
    * 0010: `gt reg_lhs reg_rhs_dest` (>, unsigned)
        * As per the ISA, the result is written into the right-hand side operand, i.e. `reg_rhs_dest`. This also holds for all other comparison operations.
        * Note that the assembler forbids comparison of a register with itself. This is to prevent bugs, and because the ISA assigns a different meaning to these instructions.
    * 0011: `gts reg_lhs reg_rhs_dest` (>, signed)
        * For this instruction, comparison with the value zero is meaningful and interesting. This can be done by simply appending `z` for `zero` to the command: `gtsz reg_value_and_dest` compiles to `0x83RR`, which is the instruction that compares the value of `reg_value_and_dest` with zero, and if it is "greater than signed zero", writes the value 0x0001 into the register; 0x0000 else.
    * 0100: `eq reg_lhs reg_rhs_dest` (==)
        * `eqz reg_value_and_dest` compares the value of `reg_value_and_dest` with the value zero, and writes it to `reg_value_and_dest`.
    * 0101: cannot be generated (same as `eq reg_lhs reg_rhs_dest`)
    * 0110: `ge reg_lhs reg_rhs_dest` (>=, unsigned)
    * 0111: `ges reg_lhs reg_rhs_dest` (>=, signed)
        * `gesz reg_value_and_dest` compares the value of `reg_value_and_dest` with the value zero, and writes it to `reg_value_and_dest`.
    * 1000: `lt reg_lhs reg_rhs_dest` (<, unsigned)
    * 1001: `lts reg_lhs reg_rhs_dest` (<, signed)
        * `ltsz reg_value_and_dest` compares the value of `reg_value_and_dest` with the value zero, and writes it to `reg_value_and_dest`.
    * 1010: `ne reg_lhs reg_rhs_dest` (!=)
        * `nez reg_value_and_dest` compares the value of `reg_value_and_dest` with the value zero, and writes it to `reg_value_and_dest`.
    * 1011: cannot be generated (same as `ne reg_lhs reg_rhs_dest`)
    * 1100: `le reg_lhs reg_rhs_dest` (<=, unsigned)
    * 1101: `les reg_lhs reg_rhs_dest` (<=, signed)
        * `lesz reg_value_and_dest` compares the value of `reg_value_and_dest` with the value zero, and writes it to `reg_value_and_dest`.
    * 1110: cannot be generated (same as `lw reg_rhs_dest 1`)
    * 1111: cannot be generated (same as `lw reg_rhs_dest 1`)
- 1001: Branch
    * `b reg_cond ( imm_offset | _lab_destination )`
        * Both forms result in the same kind of instruction. Therefore, both only support branch-offsets in the range \[-128, +129\], and the 129 is not a typo.
        * Support for longer jumps is currently missing, but should ideally be a separate instruction (to preserve predictability).
        * Offsets 0 (infinite loop) and 1 (noop) cannot be encoded in the ISA, and therefore not supported by the assembler.
        * The label does not need to be defined yet; forward-references are fine. For more info, see [directives](#directives).
- 1010: Jump by immediate
    * `j ( imm_offset | _lab_destination )`
        * Both forms result in the same kind of instruction. Therefore, both only support branch-offsets when `-(1 + 0x7FF) <= offset <= (2 + 0x7FF)`.
        * Support for longer jumps is currently missing, but should ideally be a separate instruction (to preserve predictability).
        * Offsets 0 (infinite loop) and 1 (noop) cannot be encoded in the ISA, and therefore not supported by the assembler.
        * The label does not need to be defined yet; forward-references are fine. For more info, see [directives](#directives).
    * `j _lab_destination imm_delta`
        * Under the hood, label and immediate are folded into a single immediate offset. The above restrictions hold.
- 1011: Jump to register
    * `j reg_destination [ imm_delta ]`
        * Note that the value of `reg_destination` is allowed to be arbitrary. This method of jumping is *always* possible, which is especially handy if "Jump by immediate" fails.
        * The delta must be `(-0x80 <= imm_delta <= 0x7F)`
- 1100: Jump to register high
    * `jhi reg_destination_low_byte [ imm_high_byte ]`
        * Note that the value of `reg_destination_low_byte` is allowed to be arbitrary. This method of jumping is *always* possible, which is especially handy if "Jump by immediate" fails, and no register .
        * The delta must be `(-0x80 <= imm_delta <= 0x7F)`
- 1101: reserved, cannot be generated
- 1110: reserved, cannot be generated
- 1111:
    * 0000-1110: reserved, cannot be generated
    * 1111: `ill` (illegal instruction)

## Directives

This is the juicy part, and main point of having an assembler: Special directives! Otherwise, one could just as well use a hexeditor.

- `.label _lab_name`: Remembers the current position of the write pointer for future/past use. This directive does not generate any code, so a jump like `j _lab_name` would point to the instruction right after the `.label` directive.
- `.offset imm_absolute_position`: Move the write pointer to the word at offset `imm_absolute_position`.
- `.offset _lab_absolute_position`: Move the write pointer to an already-defined label. This is the only place where the label must already be defined when used.
- `.word imm_value`: Write the literal word. Recall that the assembler generates the instruction segment, so this directive can be used to generate otherwise ungeneratable instructions, or inject read-only memory that can be recalled with `lwi`.
- `.assert_hash hexstring`: The given hexstring must be exactly 64 characters long (no spaces etc.). When the assembler is done and the instruction segment is about to be written out, the SHA256 of the segment is computed, and compared against the given hexstring. In case of a mismatch, compilation is aborted. I use this to ensure that changes in the assembler will not silently change the generated segments.
- And finally, comments: After the first `#`, the rest of the line is ignored. (Not technically a directive, but you get the point.)

## Pseudo-instructions

Finally, some instructions are so useful, so "made" to be used in a particular combination, that it just makes sense to have the assembler accept pseudo-instructions for them.
- `lw reg_dest, imm_large_value`
    * This pseudo-instruction may generate one or two instructions, and will accept any `-0x8000 <= imm_large_value <= 0xFFFF`.
    * If `imm_large_value` cannot be loaded in a single instruction, the assembler instead emits the two instructions:
      ```
      lw reg_dest, imm_low_bits
      lhi reg_dest, imm_high_bits
      ```
- `la reg_dest, lab_reference`
    * This pseudo-instruction generates always exactly one instruction, in particular it will behave like `lw reg_dest, imm_small`, where `imm_small` is the absolute address of `lab_reference`.
    * It is short for "load address".
    * As a consequence, this pseudo-instruction only works, if the label is in the range `[0x0000, 0x007F]` or in `[0xFF80, 0xFFFF]`.
    * TODO: Permit an optional immediate afterwards, i.e. `la r0, _myfunction_start +8`
- `nop` always generates exactly one instruction. Currently, it is `0x5F00`, equivalent to the hypothetical `mov r0, r0`.
- `bgt reg_lhs reg_rhs_dest ( imm_offset | _lab_destination )`
    * Also with other comparisons: `bgts`, `beq`, `bge`, `bges`, `blt`, `blts`, `bne`, `ble`, `bles`
    * Also with the zero comparisons: `bgtsz`, `beqz`, `bgesz`, `bltsz`, `bnez`, `blesz`
    * The assembler *usually* instead emits the two instructions:
      ```
      gt reg_lhs reg_rhs_dest
      b reg_rhs_dest ( imm_offset | _lab_destination )
      ```
    * Except in the case of `bnez`, which actually simplifies to a single instruction: `b reg_rhs_dest ( imm_offset | _lab_destination )`
    * The same restrictions as to `b` apply:
        * This pseudo-instruction only supports branch-offsets in the range \[-128, +129\], and the 129 is not a typo.
        * Offsets 0 (infinite loop) and 1 (noop) cannot be encoded in the ISA, and therefore not supported by the assembler.
        * The label does not need to be defined yet; forward-references are fine. For more info, see [directives](#directives).
- For medium-long branches, `lb reg_cond ( imm_offset | _lab_destination )` works with 12-bit relative offsets.
    * Note that `lb` must first invert the condition (`eqz reg_cond`), the conditionally skip the next instruction (`b reg_cond +2`), then jump-immediate to the desired destination (`j ( imm_offset | _lab_destination )`).
    * This means that `reg_cond` ends up with the *opposite* of the original boolean value. This is usually fine, since it is often discarded    anyway.
    * These three instructions are obviously somewhat expensive, and the assembler will prevent accidental use below some threshold, although not the entire range \[-128, +129\] is flagged, only \[-118, +119\]. This is to allow for some slack when code offsets are changing while programming.
    * If the extended range is really necessary, you might want to use one of the following pseudo-instructions to merge it with a preceding comparison:
        * `( lbeq | lbge | lbges | lbgt | lbgts | lble | lbles | lblt | lblts | lbne ) reg_lhs reg_rhs_dest ( imm_offset | _lab_destination )`
        * `( lbeqz | lbgesz | lbgtsz | lblesz | lbltsz | lbnez ) reg_value ( imm_offset | _lab_destination )`
        * Note that, again, `reg_rhs_dest` (or `reg_value`) is usually overwritten with the *opposite* of the resulting boolean value.
        * These medium-longbranch-comparison pseudo-instructions will usually compile down to just three instructions:
          ```
          cmp_opposite reg_lhs reg_rhs_dest  # or "cmp_opposite_z reg_value"
          b reg_rhs_dest +2
          j ( imm_offset | _lab_destination )
          ```
        * Except in the case of `lbeqz`, which actually simplifies to two instructions, because `nez` is not required:
          ```
          b reg_value +2
          j ( imm_offset | _lab_destination )
          ```
    * All forms result in the same kind of instruction sequence. Therefore, they only support branch-offsets in the range \[-2048, 2049\], and the 2049 is not a typo.
    * Support for even longer jumps is currently missing, but should ideally be a separate pseudo-instruction (to preserve predictability).
    * Offsets 0 (infinite loop) and 1 (noop) cannot be encoded in the ISA, and therefore not supported by the assembler.
    * The label does not need to be defined yet; forward-references are fine. For more info, see [directives](#directives).
- `lla reg_dest, lab_reference`
    * This pseudo-instruction generates always exactly two instructions, in particular it will behave like `lw reg_dest, imm_large_value`, where `imm_large_value` is the absolute address of `lab_reference`.
    * It is short for "long load address".
    * This pseudo-instruction works for labels at all offsets.
    * If, however, the offset is close to zero, a warning is emitted, to inform the user that one instruction can be saved by using `la` instead. This is similar to `lb`: Not the entire range \[-128, +127\] is flagged, only \[-118, +117\]. This is to allow for some slack when code offsets are changing while programming.
    * TODO: Permit an optional immediate afterwards, i.e. `lla r0, _myfunction_start +8`
