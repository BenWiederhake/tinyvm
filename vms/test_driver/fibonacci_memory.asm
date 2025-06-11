# Format: See ../../assembler/README.md

# Computes the nth fibonacci number, if starting from 0xFF80, and r0 is the number n.
.assert_hash 61D21CB9512296FBFB7C64DEEC114C2836C70A7D494540833117F8FF39446EBD

ill  # Execution is meant to start at 0xFF80.

.offset 0xFF80
lw r1, 0x0001
lw r1, r1
bnez r1 _filling_done

# Load and write starting conditions:
lw r8, 1
lw r9, 1
lw r10, 0
sw r10, r8
incr r10
sw r10, r9
incr r10

lw r11, 30  # num items
.label _fill_loop_start
# compute next element:
mov r7, r8
mov r8, r9
add r7 r9
# write next element:
sw r10, r9
incr r10
# advance:
decr r11
bnez r11 _fill_loop_start

.label _filling_done
lw r0, r0
yield
