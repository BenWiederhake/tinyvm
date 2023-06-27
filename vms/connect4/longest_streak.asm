# Format: See ../../assembler/README.md
# Data layout: See ../../data-layout/connect4.md

# Play such that the longest streak is maximized.
.assert_hash 7A1704095E0EE57ABA6148E35C1B9B4EDA85F9067F0C1025D3971F350C8E6419

# r0-r2: temporary
# r7: currently-considered streak, other direction
# r8: currently-considered streak
# r10: best streak length
# r11: best streak x
# r12: x
# r13: y
# r14: Width
# r15: Height

lw r11, 0xFFFF

lw r14, 0xFF86 # "0xFF86: Width of the board."
lw r14, r14
lw r15, 0xFF87 # "0xFF87: Height of the board."
lw r15, r15

.label _enum_candidates_check_next_position
    # Invariant: x and y are legal coordinates, and positions with lower y are all filled.
    # if (slot[x][y] != 0) { goto _enum_candidates_incr_y; }
    mov r0, r12
    mul r15 r0
    add r13 r0
    lw r0, r0
    lbnez r0 _enum_candidates_incr_y

    # First, look at how long the vertical streak would be.
    # For that, we only need to look downward (y minus, x zero)
    # i = 1
    lw r8, 1
.label _check_ymx0_next
    # check_y = y - i; if (check_y < 0) { goto _check_ymx0_done_counting; }
    mov r0, r8
    sub r13 r0
    mov r1, r0
    bltsz r1 _check_ymx0_done_counting
    # check_index = x * HEIGHT + check_y
    mov r1, r12
    mul r15 r1
    add r0 r1
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r1
    decr r0
    # if (content != 0) { goto _check_ymx0_done_counting; }
    b r0 _check_ymx0_done_counting
    # Great! This continues the streak downward.
    # i += 1; goto start_of_loop;
    incr r8
    j _check_ymx0_next
.label _check_ymx0_done_counting
    # if {i > best_streak} { best_streak = i; best_move = x; }
    mov r0, r8
    bge r10 r0 _check_ymx0_over
    mov r10, r8
    mov r11, r12
.label _check_ymx0_over

    # How long would the horizontal streaks be?
    # First, check to the left (x minus, y zero)
    # i = 1
    lw r8, 1
.label _check_xmy0_next
    # check_x = x - i; if (check_x < 0) { goto _check_xpy0_begin; }
    mov r0, r8
    sub r12 r0
    mov r1, r0
    bltsz r1 _check_xpy0_begin
    # check_index = check_x * HEIGHT + y
    mul r15 r0
    add r13 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xpy0_begin; }
    b r0 _check_xpy0_next
    # Great! This continues the streak to the left.
    # i += 1; goto start_of_loop;
    incr r8
    j _check_xmy0_next
.label _check_xpy0_begin
    # Next, check to the right (x plus, y zero)
    # j = 1
    lw r7, 1
    # fall-through
.label _check_xpy0_next
    # check_x = x + j; if (check_x >= WIDTH) { goto _check_xmpy0_done_counting; }
    mov r0, r7
    add r12 r0
    mov r1, r14
    bge r0 r1 _check_xmpy0_done_counting
    # check_index = check_x * HEIGHT + y
    mul r15 r0
    add r13 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xmpy0_done_counting; }
    b r0 _check_xmpy0_done_counting
    # Great! This continues the streak to the right.
    # j += 1; goto start_of_loop;
    incr r7
    j _check_xpy0_next
.label _check_xmpy0_done_counting
    # Note that "i + j" would double-count the hypothetical stone that we're considering to play. Therefore:
    # found_streak = i + j - 1
    add r7 r8
    decr r8
    # if {found_streak > best_streak} { best_streak = i; best_move = x; }
    mov r0, r8
    bge r10 r0 _check_xmpy0_over
    mov r10, r8
    mov r11, r12
.label _check_xmpy0_over

    # How long would the diagonal1 (/) streaks be?
    # First, check to the left down (x minus, y minus)
    # i = 1
    lw r8, 1
.label _check_xmym_next
    # check_x = x - i; if (check_x < 0) { goto _check_xpyp_begin; }
    mov r0, r8
    sub r12 r0
    mov r1, r0
    bltsz r1 _check_xpyp_begin
    # check_y = y - i; if (check_y < 0) { goto _check_xpyp_begin; }
    mov r1, r8
    sub r13 r1
    mov r2, r1
    bltsz r2 _check_xpyp_begin
    # check_index = check_x * HEIGHT + check_y
    mul r15 r0
    add r1 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xpyp_begin; }
    b r0 _check_xpyp_begin
    # Great! This continues the streak to the left down.
    # i += 1; goto start_of_loop;
    incr r8
    j _check_xmym_next
.label _check_xpyp_begin
    # Next, check to the right up (x plus, y plus)
    # j = 1
    lw r7, 1
    # fall-through
.label _check_xpyp_next
    # check_x = x + j; if (check_x >= WIDTH) { goto _check_xmpymp_done_counting; }
    mov r0, r7
    add r12 r0
    mov r1, r14
    bge r0 r1 _check_xmpymp_done_counting
    # check_y = y + j; if (check_y >= HEIGHT) { goto _check_xmpymp_done_counting; }
    mov r1, r7
    add r13 r0
    mov r2, r15
    bge r1 r2 _check_xmpymp_done_counting
    # check_index = check_x * HEIGHT + check_y
    mul r15 r0
    add r1 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xmpymp_done_counting; }
    b r0 _check_xmpymp_done_counting
    # Great! This continues the streak to the right up.
    # j += 1; goto start_of_loop;
    incr r7
    j _check_xpyp_next
.label _check_xmpymp_done_counting
    # Note that "i + j" would double-count the hypothetical stone that we're considering to play. Therefore:
    # found_streak = i + j - 1
    add r7 r8
    decr r8
    # if {found_streak > best_streak} { best_streak = i; best_move = x; }
    mov r0, r8
    bge r10 r0 _check_xmpymp_over
    mov r10, r8
    mov r11, r12
.label _check_xmpymp_over

    # How long would the diagonal2 (\) streaks be?
    # First, check to the left up (x minus, y plus)
    # i = 1
    lw r8, 1
.label _check_xmyp_next
    # check_x = x - i; if (check_x < 0) { goto _check_xpym_begin; }
    mov r0, r8
    sub r12 r0
    mov r1, r0
    bltsz r1 _check_xpym_begin
    # check_y = y + i; if (check_y >= HEIGHT) { goto _check_xpym_begin; }
    mov r1, r8
    add r13 r1
    mov r2, r15
    bge r1 r2 _check_xpym_begin
    # check_index = check_x * HEIGHT + check_y
    mul r15 r0
    add r1 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xpym_begin; }
    b r0 _check_xpym_begin
    # Great! This continues the streak to the left down.
    # i += 1; goto start_of_loop;
    incr r8
    j _check_xmyp_next
.label _check_xpym_begin
    # Next, check to the right down (x plus, y minus)
    # j = 1
    lw r7, 1
    # fall-through
.label _check_xpym_next
    # check_x = x + j; if (check_x >= WIDTH) { goto _check_xmpypm_done_counting; }
    mov r0, r7
    add r12 r0
    mov r1, r14
    bge r0 r1 _check_xmpypm_done_counting
    # check_y = y - j; if (check_y < 0) { goto _check_xmpypm_done_counting; }
    mov r1, r7
    sub r13 r1
    mov r2, r1
    bltsz r2 _check_xmpypm_done_counting
    # check_index = check_x * HEIGHT + check_y
    mul r15 r0
    add r1 r0
    # content = slot[check_index] - 1
    # "1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player."
    lw r0, r0
    decr r0
    # if (content != 0) { goto _check_xmpypm_done_counting; }
    b r0 _check_xmpypm_done_counting
    # Great! This continues the streak to the right up.
    # j += 1; goto start_of_loop;
    incr r7
    j _check_xpym_next
.label _check_xmpypm_done_counting
    # Note that "i + j" would double-count the hypothetical stone that we're considering to play. Therefore:
    # found_streak = i + j - 1
    add r7 r8
    decr r8
    # if {found_streak > best_streak} { best_streak = i; best_move = x; }
    mov r0, r8
    bge r10 r0 _check_xmpypm_over
    mov r10, r8
    mov r11, r12
.label _check_xmpypm_over

j _enum_candidates_incr_x

.label _enum_candidates_incr_y
# if (++y < HEIGHT) { goto _enum_candidates_check_next_position; }
incr r13
mov r0, r13
lbgt r15 r0 _enum_candidates_check_next_position
# fall-through

.label _enum_candidates_incr_x
# y = 0; if (++x < WIDTH) { goto _enum_candidates_check_next_position; }
lw r13, 0
incr r12
mov r0, r12
lbgt r14 r0 _enum_candidates_check_next_position

mov r0, r11
ret
