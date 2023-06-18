# Format: See ../../assembler/README.md
# Data layout: See ../../data-layout/connect4.md

# Try to play in the column of the opponent, or choose a random one if it's already full.
.assert_hash E42973C11399F83D2142CA9759988652C3E5436F1E0C4C338E4A8E92061291FD

# r0-r7: Temporaries
# r10: always zero
# r13: Considered column
# r14: Width of the board
# r15: Height of the board
# Hmm, register aliases would be nice.

lw r0, 0xFF87 # "0xFF87: Height of the board."
lw r15, r0
lw r0, 0xFF86 # "0xFF86: Width of the board."
lw r14, r0
lw r0, 0xFF8A # "0xFF8A: Last move by other player."
lw r13, r0

# if (last_move == 0xFFFF) { goto _do_try_again; }
lw r0, 0xFFFF
eq r13 r0
b r0 _do_try_again

.label _check_column_or_try_again
# Is there an empty slot at the top of that column?
# index = (x + 1) * HEIGHT - 1;
incr r0, r13
mul r15 r0
decr r0
# if (memory[index] == 0) { goto _done; }
lw r1, r0
eq r10 r1
b r1 _done
.label _do_try_again
# That column doesn't work. Try a different column:
decr r0, r14
rnd r13, r0
j _check_column_or_try_again

.label _done
mov r0, r13
ret
