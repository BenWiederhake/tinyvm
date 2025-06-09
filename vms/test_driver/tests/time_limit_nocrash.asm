# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash E3A88A1EC410C53953F553368C37C7804DDFC18742D522A63C346E308F89E44F

# Can set it to minimum:
lw r0, 8  # "set testee time limit"
lw r1, 0x0000
lw r2, 0x0000
lw r3, 0x0001
yield

# Can set it to maximum:
lw r0, 8  # "set testee time limit"
lw r1, 0xFFFF
lw r2, 0xFFFF
lw r3, 0xFFFF
yield

# Can set it to pseudo-random value:
lw r0, 8  # "set testee time limit"
lw r1, 0x5C48
lw r2, 0x6D43
lw r3, 0x1934
yield

# If we still didn't crash, then "the test" is successful:
lw r0, 0
lw r9, 1  # "test passed"
sw r0, r9
incr r0
lw r9, 0x650D  # first magic word
sw r0, r9
incr r0
lw r9, 0x4585  # second magic word
sw r0, r9

# Signal to the environment that we're done.
lw r0, 2  # "done"
lw r1, 1  # num tests
yield
