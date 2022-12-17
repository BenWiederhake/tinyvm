# On the nth move, place in column n % 7
.assert_hash 6FB82CD45B48C3B1CC191D6DA054571701B6A06301BD4E33797886F8E62D27F3

lw r1, 0xFF89 # Address of total number of moves made by this player.
lw r1, r1
lw r0, 7
modu r1 r0
ret
