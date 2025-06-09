# Format: See ../../assembler/README.md

# Just a simple read/write test. Doesn't even try to execute the testee.
.assert_hash BBC8CBE5CDE8478EDB434917CA59379A70BB2E56AF818EE1DDE750EF95C9D7D6

# Can set it to the beginning:
lw r0, 9  # "set testee program counter"
lw r1, 0x0000
yield

# Can set it to the end:
lw r0, 9  # "set testee program counter"
lw r1, 0xFFFF
yield

# Can set it to something arbitrary:
lw r0, 9  # "set testee program counter"
lw r1, 0xABCD
yield

# Can set it to something pseudo-random:
lw r0, 9  # "set testee program counter"
lw r1, 0xC5FD
yield

# Can set it to something pseudo-random low-ish:
lw r0, 9  # "set testee program counter"
lw r1, 0x3F34
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
