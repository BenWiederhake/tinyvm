# Format: See ../../assembler/README.md
# Data layout: See ../../data-layout/connect4.md

# Play alternatingly in the first two columns, but be as slow about it as possible.
# The point is to make sure that the worst-case performance doesn't cause terrible issues.
# That said, please don't write more tests that just burn CPU time. Feel free to use it for productive things, but this is silly.
.assert_hash 595AD5B67B964DC34EB9CA5F7D8096846C2733D129575172FAB86CCE85683738

# r0-r3: Time values
# r4-r7: Temporaries
# r9: Intended column
# r10: (constant) zero
# r11: (constant) max available time most significant word
# r12: (constant) max available time
# r13: (constant) max available time
# r14: (constant) max available time least significant word
# r15: (constant) number of instructions needed to safely finish
# Hmm, register aliases would be nice.

lw r4, 0xFF89 # "0xFF89: Total number of moves made by this player."
lw r4, r4
incr r4
lw r9, 2
modu r4 r9

# Read available time
lw r11, 0xFF82 # "0xFF82: Total time available for this move, in 4 words, most significant word first"
lw r11, r11
lw r12, 0xFF83
lw r12, r12
lw r13, 0xFF84
lw r13, r13
lw r14, 0xFF85
lw r14, r14

# We get the time at label _countdown_more, then compute how many steps we have after that.
# If we decide to loop, we will spend at least another loop and the epilogue in terms of time.
# A single loop is exactly 25 instructions, the epilogue is two instructions.
lw r15, 52

.label _countdown_more
time
# == Compute remaining time from r0..r3 into r0..r3:
# Step 1: r3 = r14 - r3; if (overflow) r2 -= 1;
sub r14 r3
mov r4, r3
lt r14 r4 # r4 now contains the carry
sub r2 r4
mov r2, r4
# Step 2: r2 = r13 - r2; if (overflow) r1 -= 1;
sub r13 r2
mov r4, r2
lt r13 r4 # r4 now contains the carry
sub r1 r4
mov r1, r4
# Step 3: r1 = r12 - r1; if (overflow) r0 -= 1;
sub r12 r1
mov r4, r1
lt r12 r4 # r4 now contains the carry
sub r0 r4
mov r0, r4
# Step 4: r0 = r11 - r0;
sub r11 r0
# == Check if we have sufficient time for this and the next iteration:
ne r10 r0
b r0 _countdown_more
ne r10 r1
b r1 _countdown_more
ne r10 r2
b r2 _countdown_more
# if (MIN_REQUIRED_INSN_LEFT < r3) { goto _countdown_more; }
lt r15 r3
b r3 _countdown_more

mov r0, r9
ret
