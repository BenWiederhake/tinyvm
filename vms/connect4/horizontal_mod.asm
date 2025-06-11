# Format: See ../../assembler/README.md

# Play in a random valid (but possibly full) column.
.assert_hash 328CE29147B1567C2CA3C164841BCCDF32E597C294458AE95A1A1657FA337568

# Use r4 as counter, and r5 as scratch space

.label _start
# The value for this move is already stored in r4 (initially zero):
mov r0, r4
# Prepare for the next move:
incr r5, r4
mov r4, r1  # r1 is the width of the board
modu r5 r4
yield
j _start
