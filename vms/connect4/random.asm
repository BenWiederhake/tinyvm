# Format: See ../../assembler/README.md

# Play in a random valid (but possibly full) column.
.assert_hash 62143B24DC2F2EE5CE81D26D247BB28D8D9CFCBB4C183D93D73BA8A56DAC2340

.label _start
decr r1
rnd r0, r1
yield
j _start
