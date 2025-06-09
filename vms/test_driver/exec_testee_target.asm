# Format: See ../../assembler/README.md

# Some marginally interesting behavior when started at various locations.
.assert_hash 7218EB834E4B886775679D78137883E0AE2237D30F0CF7E254FC4B8FE85008DB

ill  # Fail if anyone tried "bare-bones" execution

.offset 0x0100
lw r0, 0xA580  # Some pseudo-random value that's unlikely to match by pure chance
yield
ill

.offset 0x0200
lw r0, 0x526B  # Some pseudo-random value that's unlikely to match by pure chance
yield
lw r0, 0xEDEC  # Some pseudo-random value that's unlikely to match by pure chance
yield
ill

.offset 0x0300
.word 0xF22A  # pseudo-random illegal instruction

.offset 0x0400
# several single-instruction loads, to test time limits:
lw r0, 0x50
lw r1, 0x51
lw r2, 0x52
lw r3, 0x53
lw r4, 0x54
lw r5, 0x55
lw r6, 0x56
lw r7, 0x57
lw r8, 0x58
lw r9, 0x59
lw r10, 0x5A
yield
ill  # should not be reached
