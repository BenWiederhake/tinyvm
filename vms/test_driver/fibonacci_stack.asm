# Format: See ../../assembler/README.md

# Computes the nth fibonacci number, if starting from 0xFF80, and r0 is the number n.
.assert_hash F23EC133842EBE07CE2A2BFCA30A10F77BFB9ACEF630062A46D56DDD561F973B

# Calling convention:
# - r15 points to the lowest valid address of the stack (of 0x0000 if the stack is empty)
# - r14 contains the return address
# - r0 is the argument (how should this generalize? r0-r7, perhaps?)
# - r0 is also the return value (how should this generalize? r0-r7, perhaps?)
# - r8 is a scratch register (caller-saved)

ill  # Execution is meant to start at 0xFF80.

.offset 0x0010
.label _fib_start

# if (arg < 2) { return 1; }
lw r1, 2
bge r0 r1 _fib_nontrivial
lw r0, 1
j r14
# else
.label _fib_nontrivial

# Push return addr to the stack
decr r15
sw r15, r14
# Push n-1 to the stack
decr r8, r0
decr r15
sw r15, r8
# Stack is now [ n-1, ret_addr ]

# Compute fib(n-2):
decr r0, r8
la r14, _fib_after_first_call
j _fib_start
.label _fib_after_first_call
# Stack is again [ n-1, ret_addr ]

mov r1, r0
lw r0, r15
sw r15, r1
# Stack is now [ fib(n-2), ret_addr ]

# Compute fib(n-1):
la r14, _fib_after_second_call
j _fib_start
.label _fib_after_second_call

# Pop fib(n-2):
lw r8, r15
incr r15
# Pop return address:
lw r14, r15
incr r15
# Compute result:
add r8 r0
j r14

.offset 0xFF80
lw r15, 0  # (Re-)initialize the stack
# Push return address to stack:
la r14, _main_fib_return_addr
# Call fib(n):
j _fib_start
# fib(n) comes back here, because we pushed it to the stack:
.label _main_fib_return_addr
# Let the driver analyze r0 and r15.
yield
