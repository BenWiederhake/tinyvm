# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash DCBAE3B3B59321573F3F8864ED31F19F7B410FA8BCE9C4324BBAA5EF947BE0A5

# TODO: Write a test where src or dst wrap around.

# Prepare first write:
lw r0, 16  # remaining items
lw r1, 0x0100  # dst location (own data segment)
la r2, _random_data_one_start  # src location (own instruction segment)
.label _memcpy_one_start
lwi r3, r2
sw r1, r3
decr r0
incr r1
incr r2
bnez r0 _memcpy_one_start

# Write these bytes to the testee:
lw r0, 4  # "memcpy from own data segment to testee data segment"
lw r1, 0xABCD  # dst ptr
lw r2, 0x0100  # src ptr
lw r3, 16  # num items
yield

# Prepare second write:
lw r0, 12  # remaining items
lw r1, 0x0200  # dst location (own data segment)
la r2, _random_data_two_start  # src location (own instruction segment)
.label _memcpy_two_start
lwi r3, r2
sw r1, r3
decr r0
incr r1
incr r2
bnez r0 _memcpy_two_start

# Write these bytes to the testee as well:
lw r0, 4  # "memcpy from own data segment to testee data segment"
lw r1, 0xABD5  # dst ptr, shifted by eight (partial overwrite)
lw r2, 0x0200  # src ptr
lw r3, 12  # num items
yield

# Make the target region dirty, so that we know for certain that it was overwritten during "yield":
lw r0, 32  # number remaining
lw r1, 0x0300  # dst ptr
lw r2, 0x5A5A  # value
.label _dirty_loop_begin
sw r1, r2
incr r1
decr r0
bnez r0 _dirty_loop_begin

# Read them back:
lw r0, 5  # "memcpy from testee data segment to own data segment"
lw r1, 0x0300  # dst ptr
lw r2, 0xABCD  # src ptr
lw r3, 24  # num items (Catch all bytes plus some trailing zero bytes)
yield

# Pretend that each of the 32 bytes (including "dirty bytes") is a test. First, write the end marker:
lw r0, 32  # one past test results
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

# Check each byte, write the result:
lw r0, 32  # num items remaining
la r1, _expect_data_start  # address of expected
lw r2, 0x0300  # address of actual
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
lw r1, 32  # num tests
yield

# Some random data itself
.offset 0xFF80
.label _random_data_one_start
.word 0x3EE8
.word 0x8DBB
.word 0xA097
.word 0x001C
.word 0x3FCE
.word 0x1F5C
.word 0xC08F
.word 0x27A4
.word 0x5A06
.word 0x55AF
.word 0x1B6F
.word 0x1889
.word 0x4AC8
.word 0x4007
.word 0x5E70
.word 0x6430

.offset 0xFF90
.label _random_data_two_start
.word 0xB773
.word 0xF089
.word 0x9A7F
.word 0x5A38
.word 0xA993
.word 0xCB7E
.word 0xD5AE
.word 0x521F
.word 0xACA6
.word 0xFDF7
.word 0x78BF
.word 0x6DBF
# Some words undefined

.offset 0xFFA0
.label _expect_data_start
.word 0x3EE8
.word 0x8DBB
.word 0xA097
.word 0x001C
.word 0x3FCE
.word 0x1F5C
.word 0xC08F
.word 0x27A4
.word 0xB773
.word 0xF089
.word 0x9A7F
.word 0x5A38
.word 0xA993
.word 0xCB7E
.word 0xD5AE
.word 0x521F
.word 0xACA6
.word 0xFDF7
.word 0x78BF
.word 0x6DBF
.word 0
.word 0
.word 0
.word 0
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
.word 0x5A5A
