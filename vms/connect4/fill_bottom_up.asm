# Format: See ../../assembler/README.md
# Data layout: See ../../data-layout/connect4.md

# Try to play at the lowest possible y-coordinate.
.assert_hash 44BFDEE44CF5D8667556998D24F6F1849184910118E226174ADC88835AE0EF45

# r0: x
# r1: y
# r2: temporary
# r10: constant zero
# r13: index
# r14: Width
# r15: Height

lw r14, 0xFF86 # "0xFF86: Width of the board."
lw r14, r14
lw r15, 0xFF87 # "0xFF87: Height of the board."
lw r15, r15

# Optimization: x and y are already initialized to 0 - good, exactly what we want (top right).
# Optimization: index is already initialized to 0 - good, because index(0, 0) == 0.

.label _return_if_free
# if (cell[x][y] != 0) { goto _next_cell; }
lw r2, r13
ne r10 r2
b r2 _next_cell
# return x;
ret

.label _next_cell
incr r0
# if (x < Width) { goto _recompute_index; }
mov r2, r14
lt r0 r2
b r2 _recompute_index
# x = 0; y += 1;
lw r0, 0
decr r1
# fall-through

.label _recompute_index
mov r13, r0
mul r15 r13
add r1 r13
j _return_if_free
