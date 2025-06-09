# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash C333C3166B9F39A6CC708438CD75E4F6427C744D4AC498F0CCA081EE110D7537

# Prepare some values in memory:
lw r8, 0x0104
lw r9, 0xABCD  # value to be loaded
sw r8, r9
incr r8
lw r9, 0x6419  # pseudo-random
sw r8, r9
incr r8
lw r9, 0x3456  # value to be overwritten
sw r8, r9

# Load them into the testee:
lw r0, 3  # "access registers"
lw r1, 0x0030  # Write registers 4 and 5 to the testee
lw r2, 0x0100  # Operate at offset 0x0100
yield

# Make the target region dirty, so that we know for certain that it was overwritten during "yield":
lw r0, 16  # number remaining
lw r8, 0x0110
lw r9, 0x5A5A
.label _dirty_loop_begin
sw r8, r9
incr r8
decr r0
bnez r0 _dirty_loop_begin

# Read the resulting registers:
lw r0, 3  # "access registers"
lw r1, 0x0000  # Read-only
lw r2, 0x0110  # Operate at offset 0x0110
yield

# Pretend that each of the 32 measurements is a test. Work backwards:
lw r0, 33  # number remaining (plus one)
lw r9, 0x4585  # second magic word of the two
sw r0, r9
decr r0
lw r9, 0x650D  # first magic word of the two
sw r0, r9
lw r8, 0xFFCF  # address of last expected value, should be equal to _expected_data_last
lw r4, 0x011F  # address of last actual value
.label _check_loop_begin
# Invariant: r0 is the number of registers that still need to be checked at _check_loop_begin
decr r0
lwi r9, r8  # read expected value
lw r5, r4  # read actual value
ne r9 r5  # Write the result in r5 (0 for equal, 1 for non-equal)
incr r5  # Convert to test result enum (1 for pass, 2 for fail)
sw r0, r5  # Write out test result
decr r4
decr r8
bnez r0 _check_loop_begin

# Signal to the environment that we're done.
lw r0, 2  # "done"
lw r1, 32  # num tests
yield

# The expected data itself
.offset 0xFFB0
.word 0  # r0
.word 0  # r1
.word 0  # r2
.word 0  # r3
.word 0xABCD  # r4
.word 0x6419  # r5
.word 0  # r6, gets overwritten to zero
.word 0  # r7
.word 0  # r8
.word 0  # r9
.word 0  # r10
.word 0  # r11
.word 0  # r12
.word 0  # r13
.word 0  # r14
.word 0  # r15
.word 0  # r0
.word 0  # r1
.word 0  # r2
.word 0  # r3
.word 0xABCD  # r4
.word 0x6419  # r5
.word 0  # r6
.word 0  # r7
.word 0  # r8
.word 0  # r9
.word 0  # r10
.word 0  # r11
.word 0  # r12
.word 0  # r13
.word 0  # r14
# .label _expected_data_last  # TODO: Can't use labels as immediates to lwi (yet)
.word 0  # r15
