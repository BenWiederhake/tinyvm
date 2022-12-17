# On the nth move, place in column n % 7

lw r1, 0xFF89 # Address of total number of moves made by this player.
lw r1, r1
lw r0, 7
modu r1 r0
ret
