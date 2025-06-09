# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash 5639AD05D5A2BA8230E7A31BF889A2B18605E4DF76809AB19B3FCD7988DD3F83

# Execute from 0x0100:
lw r0, 9  # "set testee program counter"
lw r1, 0x0100  # First target
yield
lw r0, 1  # "execute testee"
yield
# Write results to 0x0070:
lw r8, 0x0070
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value

# Execute from 0x0200:
lw r0, 9  # "set testee program counter"
lw r1, 0x0200  # Second target
yield
lw r0, 1  # "execute testee"
yield
# Write results to output area:
incr r8
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value

# Continue testee execution:
lw r0, 1  # "execute testee"
yield
# Write results to output area:
incr r8
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value

# Execute from 0x0300:
lw r0, 9  # "set testee program counter"
lw r1, 0x0300  # Third target
yield
lw r0, 1  # "execute testee"
yield
# Write results to output area:
incr r8
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value

# Execute from 0x0400:
lw r0, 9  # "set testee program counter"
lw r1, 0x0400  # Fourth target
yield
lw r0, 1  # "execute testee"
yield
# Write results to output area:
incr r8
sw r8, r0  # Write testee stopping reason
incr r8
sw r8, r1  # Write testee yield value

# Pretend that each of the 10 bytes is a test. First, write the end marker:
lw r0, 10  # one past test results
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

# Check each byte, write the result:
lw r0, 10  # num items remaining
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
lw r1, 10  # num tests
yield

# The expected data:
.offset 0xFF80
# Regular yield:
.word 0x0000
.word 0xA580
# Two consecutive yields:
.word 0x0000
.word 0x526B
.word 0x0000
.word 0xEDEC
# Illegal instruction:
.word 0xFFFF
.word 0xF22A
# "Timeout", but there's no limit:
.word 0x0000
.word 0x0050

# TODO: test from 0x0400 again, but with time limits.
