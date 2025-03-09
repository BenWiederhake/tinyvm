# Format: See ../../assembler/README.md

# Play in column 0.
.assert_hash 4184F8599B65D81C8DBED24630A14E9988283F3ACE7BD9D5F7C69F33E7F745B0

.label _start
lw r0, 0 # Disregard any given value
yield
j _start
