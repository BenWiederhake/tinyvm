# Format: See ../../assembler/README.md
# Data layout: See ../../data-layout/connect4.md

# List all columns with a free slot, and play in a random one of these.
.assert_hash 38C0162CDA895F38DCD6C4E6D43CECC810D12555D7ABFA3914A09A43682AB20C

# r0-r8: Temporaries
# r10: always zero
# r11: index
# r12: x position
# r13: Height of the board
# r14: Where in memory the next column index will be written (initially 0xFFFF)
# Hmm, register aliases would be nice.

lw r14, 0xFFFF
lw r0, 0xFF87 # "0xFF87: Height of the board."
lw r13, r0
lw r0, 0xFF86 # "0xFF86: Width of the board."
lw r12, r0
decr r12

.label _analyze_column_begin_loop
# Is there an empty slot at the top of the current column?
# index = (x + 1) * HEIGHT - 1;
incr r11, r12
mul r13 r11
decr r11
# if (memory[index] != 0) { goto _analyze_column_consider_next_iteration; }
lw r0, r11
ne r10 r0
b r0 _analyze_column_consider_next_iteration
# memory[col_idx_storage] = x;
sw r14, r12
# col_idx_storage -= 1;
decr r14
.label _analyze_column_consider_next_iteration
# x -= 1;
decr r12
# if (0 <= x) { goto _analyze_column_begin_loop; }
mov r0, r12
les r10 r0
b r0 _analyze_column_begin_loop
# end loop

# num_cols_with_free_slots = -col_idx_storage - 1
not r0, r14
# max_col_lookup_index = num_cols_with_free_slots - 1
decr r0
# chosen_lookup_index = rng_up_to_including(max_col_lookup_index)
rnd r0
# memory_index = -chosen_lookup_index - 1
not r0
# TODO: assert(r14 < memory_index <= 0xFFFF)
# column = memory[memory_index]
lw r0, r0

ret
