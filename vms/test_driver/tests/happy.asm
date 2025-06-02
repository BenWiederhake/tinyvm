# Format: See ../../assembler/README.md

# Taken straight from test_driver::test_test_driver::test_done_one_pass.
.assert_hash F0B2C6BD9298113765E291A87D4CF2589CBCB43B0BE787BF3807507B4E154F13

lw r0, 2  # "done"
lw r1, 1  # num tests
lw r8, 0x0000
lw r9, 1  # "pass"
sw r8, r9
incr r8
lw r9, 0x650D
sw r8, r9
incr r8
lw r9, 0x4585
sw r8, r9
yield
