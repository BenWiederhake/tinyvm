# Format: See ../../assembler/README.md

# Computes the nth fibonacci number, if starting from 0xFF80, and r0 is the number n.
.assert_hash D88133A8DDF7ADCBA8C057BF436C2CCEF877A8F15A6A35EC72324A4A9E193B31

ill  # Execution is meant to start at 0xFF80.

.offset 0xFF80
la r1, _FIB_TABLE
add r0 r1
lwi r0, r1
yield

.offset 0x0070
.label _FIB_TABLE
# The first 24 fibonnaci numbers: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368]
.word 1
.word 1
.word 2
.word 3
.word 5
.word 8
.word 13
.word 21
.word 34
.word 55
.word 89
.word 144
.word 233
.word 377
.word 610
.word 987
.word 1597
.word 2584
.word 4181
.word 6765
.word 10946
.word 17711
.word 28657
.word 46368
