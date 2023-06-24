# Format: See ../../assembler/README.md

# Fill the board, assuming that player one is "horizontal_mod"
.assert_hash 176BC09E55C4A0056AD794FBD13EEF56199B7F32A5B0B8D8CD7A504CF610ECC5

lw r1, 0xFF89
lw r1, r1
b r1 _move_nonzero # (offset is +0x3)
# .label _move_zero # On move 0, play in column 3.
lw r0, 3
ret
.label _move_nonzero
lw r0, 18
ge r1 r0
b r0 _move_late # (offset is +0x2)
# .label _move_early # On moves 1-17, play in column (n - 1) % 7.
decr r1
# j _move_late # Surprise optimization: This is a noop, this time!
.label _move_late # On moves 18-20, play in column n % 7.
lw r0, 7
modu r1 r0
ret
