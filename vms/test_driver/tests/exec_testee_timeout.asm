# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash C1CE0D25B5CDC1B1D951F5B54A5B10AA9C8EB5CBFD50943F44D81BCF580DD623

# Only allow execution of up to 7 insns at a time:
lw r0, 8  # "set testee time limit"
lw r1, 0x0000
lw r2, 0x0000
lw r3, 0x0007
yield

# Execute from 0x0400:
lw r0, 9  # "set testee program counter"
lw r1, 0x0400  # Fourth target
yield
lw r0, 1  # "execute testee"
yield
# Write results to 0x0070:
lw r8, 0x0070
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value
# Dump registers to driver memory:
lw r0, 3  # "access testee registers"
lw r1, 0  # read-only
incr r2, r8
yield
lw r15, 16
add r15 r8

# Continue execution:
lw r0, 1  # "execute testee"
yield
# Write results to output area:
incr r8
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value
# Dump registers to driver memory:
lw r0, 3  # "access testee registers"
lw r1, 0  # read-only
incr r2, r8
yield
add r15 r8

# Pretend that each of the 36 bytes is a test. First, write the end marker:
lw r0, 36  # one past test results
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

# Check each byte, write the result:
lw r0, 36  # num items remaining
lw r1, 0xFF80  # address of expected (_expect_data_start)
lw r2, 0x0070  # address of actual
lw r3, 0  # address of result
.label _check_loop_begin
lwi r4, r1  # read expected
lw r5, r2  # read actual
ne r5 r4  # Write the result in r5 (0 for equal, 1 for non-equal)
incr r4  # Convert to test result enum (1 for pass, 2 for fail)
sw r3, r4  # Write out test result
# Advance pointers:
decr r0
incr r1
incr r2
incr r3
bnez r0 _check_loop_begin

# Signal to the environment that we're done.
lw r0, 2  # "done"
lw r1, 36  # num tests
yield

# The expected data:
.offset 0xFF80
# Timeout:
.word 0x0001
.word 0x0000
# Only 7 registers got loaded:
.word 0x0050
.word 0x0051
.word 0x0052
.word 0x0053
.word 0x0054
.word 0x0055
.word 0x0056
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
# Yield ("accidentally" 0x0050):
.word 0x0000
.word 0x0050
# All 10 registers got loaded:
.word 0x0050
.word 0x0051
.word 0x0052
.word 0x0053
.word 0x0054
.word 0x0055
.word 0x0056
.word 0x0057
.word 0x0058
.word 0x0059
.word 0x005A
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
.word 0x0000
# Dummy:
.word 0x5A5A
