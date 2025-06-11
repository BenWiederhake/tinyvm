# Format: See ../../assembler/README.md

# Checks whether the very first move in a connect4 game is valid.
.assert_hash 38488327A78A6F6D23603E739CEC06B73189053EA932126383CA57D2C8A1C956

# Limit testee time to 1000:
lw r0, 8  # "Limit testee's alotted time"
lw r1, 1000
yield

# Copy data from instruction segment to data segment:
la r0, _CONNECT4_TEMPLATE_START
la r1, _CONNECT4_TEMPLATE_END
.label _loop_copy_insn_to_data_start
lwi r2, r0
sw r0, r2
incr r0
mov r2, r0
bgt r1 r2 _loop_copy_insn_to_data_start  # loop if r0 < r1

# Write time limit notification:
lw r0, 4  # "overwrite testee data segment"
lw r1, 3  # dst ptr
la r2, _CONNECT4_TEMPLATE_0x0003_1  # src ptr
lw r3, 1  # num words
yield

# Write game version notification:
lw r0, 4  # "overwrite testee data segment"
lw r1, 0xFFFE  # dst ptr
la r2, _CONNECT4_TEMPLATE_0xFFFE_2  # src ptr
lw r3, 2  # num words
yield

# Write game registers:
lw r0, 3  # "access testee registers"
lw r1, 0x000F  # Write r0-r3
la r2, _CONNECT4_TEMPLATE_REGS_4  # src ptr
yield

# Execute:
lw r0, 1  # "execute"
yield

# Evaluate:
lw r8, 0
ne r8 r0  # "Is the stop-reason that the testee did NOT yield?"
incr r0  # Convert to 1=pass, 2=fail
mov r2, r1
ltsz r1  # "Is the chosen column negative?"
incr r1  # Convert to 1=pass, 2=fail
lw r8, 7
les r8 r2  # "Is the chosen column greater or equal to the number of columns?"
incr r2  # Convert to 1=pass, 2=fail

# Pretend that all three (in)equalities are individual tests.
lw r3, 0x650D  # first magic word
lw r4, 0x4585  # second magic word
lw r8, 0
sw r8, r0
incr r8
sw r8, r1
incr r8
sw r8, r2
incr r8
sw r8, r3
incr r8
sw r8, r4

# Signal to the environment that we're done.
lw r0, 2  # "done"
lw r1, 3  # num tests
yield

.offset 0xFF80
.label _CONNECT4_TEMPLATE_START
.label _CONNECT4_TEMPLATE_0x0003_1
.word 1000  # Total time available to the testee
.label _CONNECT4_TEMPLATE_0xFFFE_2
.word 0x0001  # Version 1
.word 0x0001  # "Connect4"
.label _CONNECT4_TEMPLATE_REGS_4
.word 0xFFFF  # "No previous move"
.word 7  # Width of the board (default)
.word 6  # Height of the board (default)
.word 0  # Must always be (re)set to zero.
# 12 more locations will be overwritten by zero when accessing testee registers.
.label _CONNECT4_TEMPLATE_END
