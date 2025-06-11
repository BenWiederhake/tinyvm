# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash 39C166947C3304203BD2C7CAC7F977F1D6568FE3981570FCEE48D886CCCD5E9D

# Pretend that each of the 10 values is a test. First, write the end marker:
lw r0, 10  # one past test results
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

lw r7, 10  # num items remaining
lw r8, 0  # input value
lw r9, 0  # output pointer
lw r10, 0x0070  # debug output pointer
la r11, _FIB_TABLE  # expected data pointer
lw r12, 0xFF80  # scratch space for register I/O

lw r0, 0x4567
sw r10, r0
incr r10

.label _loop_test_begin

# Run testee:
lw r0, 3  # "Access testee registers"
lw r1, 0x0001  # magic value indicating "the set of registers which contains only r0"
mov r2, r12  # offset of register data
sw r12, r8  # The new argument
yield  # Write the new input value as r0 to the testee
lw r0, 9  # "Set program counter"
lw r1, 0xFF80  # Magic entrypoint for test-driver-driven tests
yield
lw r0, 1  # "Execute"
yield

# Save result for debugging:
sw r10, r0
incr r10
sw r10, r1
incr r10

# Evaluate test:
lwi r3, r11  # Load expected data
bnez r0 _loop_test_iteration_fail  # Did the testee do anything other than yield?
bne r3 r1 _loop_test_iteration_fail  # Is the result wrong?
lw r0, 1  # "pass"
j _loop_test_iteration_common
.label _loop_test_iteration_fail
lw r0, 2  # "fail"
# fall-through

# Write result, advance to next
.label _loop_test_iteration_common
decr r7
incr r8
sw r9, r0
incr r9
incr r11
bnez r7 _loop_test_begin

# Signal to the environment that we're done.
lw r0, 2  # "done"
lw r1, 10  # num tests
yield

.offset 0xFF80
.label _FIB_TABLE
# The first 24 fibonnaci numbers: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368]
.word 1
.word 1
.word 2
.word 3
.word 5
.word 8
.word 13
.word 21
.word 34
.word 55
