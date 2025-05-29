# Connect4 conventions

## Miscellaneous

Two programs will play Connect4 against each other. In particular:
- At the beginning of the game, both data segments, registers and program counter are initialized to all-zeros.
- At the beginning of each move, the current game state (board, last move, number of moves, etc.) is re-written to the first few registers and first few bytes of the data segment of the player whose move it is. Note that this is in conformance to the suggested calling convention (FIXME: write it and link here), which enables programs to treat `yield` as a function call.
- The player plays a move. This is done by running the program, and yielding the desired column. Note that columns are 0-indexed, so index 0 is the first column, and index W is the first non-existing column.
- The judge decides the outcome of the move:
    * If the program times out (i.e. does not execute the Yield instruction), the game is immediately lost by that player.
    * If the program attempts to execute an illegal instruction (i.e. causes a StepResult::IllegalInstruction), the game is immediately lost by that player.
    * If the program returns a number that does not index an existing column (e.g. column 9999), the game is immediately lost by that player.
    * If the indicated column is already full (e.g. the board has a height of 6, and this column already contains 6 stones), the game is immediately lost by that player.
    * Otherwise, the move is accepted, and a token by that player is dropped into the board.
- The judge then decides if the game has ended:
    * If the moving player now has four tokens in a row, the game is won by that player.
    * If there are no more free slots, the game ends in a draw.
    * Otherwise, it is the next player's move.

The time available for each move is measured in number of instructions, and should be high enough that a simple, naive algorithm does not need to worry about it.

## Data segment content and layout for Connect4

Shorthands:
- W: The width of the board.
- H: The height of the board.
- N: The value of W * H

- starting at 0x0000, size 4 words:
    * Written before each move
    * Total time available for this move, most significant word first, similar to the returned value of the Time instruction.
- starting at 0x0004, size N words:
    * Written before each move
    * Contains the entire board. First comes the left-most column, then the rest of the W columns. In each column, first the bottom-most slot is described, then the rest of the H slots in this column. For each slot, one word is used to represent its contents: 0 for a free slot, 1 for a slot filled by the moving player's own token, 2 for a slot filled by a token of the opposing player.
    * Observe that x * H + y computes the index of the slot at coordinates (x, y)
- starting at N, size 0xFFFE - 4 - N words:
    * Written only once
    * All words are 0x0000. This region will never again be overwritten by the game; it is meant as a scratch space for the program.
- starting at 0xFFFE, size 2 words:
    * Written only once. Note that these addresses only need one instruction to be loaded.
        - 0xFFFF: Major version of the game and data: Must always be 0x0001, to distinguish it from other games. (In case someone wants to write a multi-game algorithm.)
        - 0xFFFE: Minor version of the game and data: Should be 0x0001 for the version in this document.
    * Note that under the suggested calling convention, these values will be immediately overwritten by the stack, so any multi-game algorithm would need to intentionally save these values. Likewise, if a program only plays one type of game, it suffices to completely ignore this feature.
- register 0: Last move by other player. Again, 0-indexed column. If this is the first move (and there is no previous move), this contains the value 0xFFFF.
- register 1: Width of the board.
- register 2: Height of the board.
- register 3: 0x0000
- Note that the total number of moves made by this or the other player is *not* explicitly provided. However, it can be easily deduced by keeping track of the own number of `yield` instructions, as well as checking whether the opponent's first move was at 0xFFFF.
