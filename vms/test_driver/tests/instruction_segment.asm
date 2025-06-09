# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash 4474C25D459E7E687FFD692B9D371D9E27A6F929F4B9783C7290531B56101B13

# Read beginning:
lw r0, 6  # "memcpy from testee instruction segment to own data segment"
lw r1, 0x0100  # dst ptr
lw r2, 0x0000  # src ptr
lw r3, 8  # num items
yield

# Read middle:
lw r0, 6  # "memcpy from testee instruction segment to own data segment"
lw r1, 0x0108  # dst ptr
lw r2, 0xABC8  # src ptr
lw r3, 16  # num items
yield

# Read end:
lw r0, 6  # "memcpy from testee instruction segment to own data segment"
lw r1, 0x0118  # dst ptr
lw r2, 0xFFF8  # src ptr
lw r3, 8  # num items
yield

# Read across wrap-around:
lw r0, 6  # "memcpy from testee instruction segment to own data segment"
lw r1, 0x0120  # dst ptr
lw r2, 0xFFFD  # src ptr
lw r3, 8  # num items
yield

# Pretend that each of the 40 bytes is a test. First, write the end marker:
lw r0, 40  # one past test results
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

# Check each byte, write the result:
lw r0, 40  # num items remaining
lw r1, 0xFF80  # address of expected (_expect_data_start)
lw r2, 0x0100  # address of actual
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
lw r1, 40  # num tests
yield

# The expected data:
.offset 0xFF80
# Beginning (exact)
.word 0xF379
.word 0x50A0
.word 0xBA95
.word 0x1153
.word 0x73AF
.word 0x9EBE
.word 0x0FC6
.word 0x2B2E
# Middle (5 extra in the beginning, 3 extra in the end)
.word 0
.word 0
.word 0
.word 0
.word 0
.word 0x2CEB
.word 0x9A8C
.word 0xE8CB
.word 0x363F
.word 0x0CBC
.word 0xAA1C
.word 0x2465
.word 0x6ED3
.word 0
.word 0
.word 0
# End (exact)
.word 0x38C4
.word 0xD183
.word 0xC2B9
.word 0x3AE0
.word 0x6CC0
.word 0xBE3F
.word 0x23CA
.word 0xD117
# Across wrap-around, with three from the end, and five from the beginning:
.word 0xBE3F
.word 0x23CA
.word 0xD117
.word 0xF379
.word 0x50A0
.word 0xBA95
.word 0x1153
.word 0x73AF
