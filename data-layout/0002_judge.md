# Judge conventions

## Miscellaneous

One or more programs will play a game against each other, and the judge will judge which player, if any, wins. In particular:
- At the beginning of execution, the data segment, registers and program counter are initialized to all-zeros, except for:
    * The data segment at address 0xFFFF is initialized to 0x0002 ("judge")
    * The data segment at address 0xFFFE is initialized to 0x0001 ("version 1")
    * Register 0 is initialized to the number of players (between 1 and 0x0100 inclusively)
- When the judge is ready to issue a move, it yields a special value. The registers and data segment will be evaluated according to the [Making A Move](#making-a-move) section.
- After the player has completed a move, the registers and data segment of the judge are updated according to the [Evaluating A Move](#evaluating-a-move) section.
- When the judge is ready to make a judgment (i.e. declare win, loss, draw, or error), it yields a different special value, and the data segment will be evaluated according to the [Making A Judgment](#making-a-judgment) section. Note that the judge can immediately declare an error before even allowing any moves to be made, which is especially interesting if the judge only allows a particular number of players (e.g. "less than 10", or "only an even number", or "exactly 4", or "exactly 1").

Of particular note is that the time taken by each player is subtracted from the total time budget of the judge. Therefore, the judge should either "pipe through" the time pressure to the players, declare a win/loss by timeout, or must face the reality that different runners might provide different amounts of time to the judge.

## Making A Move

In order to allow a player to make a move, the judge must indicate several things:
- which player
- allotted time
- data segment slices of the player that shall be written before the move
- registers of the player that shall be written before the move
- data segment slices of the player that shall be read after the move

This method is intentionally analogous to scatter/gather I/O operations, in order to minimize the
number of round-trips. At the same time, it is a disadvantage: A judge cannot simulate a judge,
this being one of the reasons.

This information should be arranged like so:
- Register 0 contains the player index. If there are N players, then register 0 must be in \[0, N - 1\]. (Note that 0xFFFF corresponds to [Making A Judgment](#making-a-judgment).) Yielding with any other value is treated as "declaring an error".
- The data segment must contain the remaining information:
    * starting at 0x0000, size 4 words: allotted time
    * starting at 0x0004, size 1 word: address where the content of the registers of the player shall be written. Wraps around, so if the judge specifies 0xFFFF, then 0xFFFF and 0x0000 through 0x000E are modified in the judge's data segment.
    * starting at 0x0005, size 1 word: number NW of data segment slices written to the player. Must be in \[0x0000, 0x0020\].
    * starting at 0x0006, size 1 word: number NR of data segment slices read from to the player. Must be in \[0x0000, 0x0020\].
    * starting at 0x0007, size 1 word: the number R of registers that shall be written. R must be in \[0, 14\].
    * starting at 0x0008, size 4 * NW words: write-instructions. Each quadruple A, B, C, D means: memcpy(&mut player_data[A..B], &judge_data[C, D])
        * sub-word 1: first word of the player data segment that shall be overwritten
        * sub-word 2: one past last word of the player data segment that shall be overwritten
        * sub-word 3: first word of the judge data segment that shall be used/read
        * sub-word 4: one past last word of the judge data segment that shall be used/read
        * If any pair is inconsistent or implausible (i.e. the slice has a negative size, size zero, or a size larger than 0x7FFF), an error is declared instead.
        * If the pairs have different sizes, an error is declared instead.
    * starting at 0x0008 + 4 * NW, size 4 * NR words: read-instructions. Each quadruple A, B, C, D means: memcpy(&mut judge_data[A..B], &player_data[C, D])
        * See write-instructions.
- If R is positive, then registers 1 through 1 + R - 1 are written as registers 0 through R - 1 to the player. (If R is zero, the registers of the player are not modified.)
    * Note that this also means that the frame-pointer cannot be overwritten, which is undesirable anyway.

One of the advantages is that simple data-layouts require only few updates to this segment on each
move, and judges for global-information games (i.e. those without hidden information) can even
write these few bytes once and never change them again.

Furthermore, the construction means that the highest address that can be possibly occupied by this
meta-language is 0x0107. This, plus the consistency-checking, should catch many types of overflow.

## Evaluating A Move

When a player is done, the following registers and data segment slices of the judge are modified:
- register 0: Indicates the type of control-flow break:
    * 0x0000: yield
    * 0x0001–0x000F: reserved, should indicate something positive
    * 0x0010: illegal instruction
    * 0x0011: timeout (of the time allotted by the judge; if the judge runs out, then the judge cannot become aware of this fact, as it no longer runs)
    * 0x0012–0x001F: reserved, should indicate something bad
    * 0x0020–0x7FFF: reserved?
    * 0x8000–0xFFFF: will never be used
- register 1: instructions actually executed by that player

Only in the cases 0x0000–0x000F, the previously-requested register reads and data segment reads are executed according
to the [Making A Move](#making-a-move) section. Otherwise, the judge's data segment is unchanged.

It is not advisable to continue letting a player move after it executed an illegal instruction; however, the judge may still do so.

## Making A Judgment

In order to make a deliberate judgment, the judge should yield the value 0xFFFF in register 0.
If the number of players is N, then the first N addresses in the data segment contain the signed
number of points awarded to each player. Typically, these will be -1, 0, and +1.

The judge can also "declare an error", by behaving in any illegal way, e.g. an illegal instruction
or yielding with invalid values. By convention, the judge should yield the value 0xFFFE in register
0, to indicate that something regarding the game logic failed. In contrast, an illegal move by a
player should cause that player's loss; "declaring an error" would not be appropriate here.
