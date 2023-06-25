use crate::vm::{Segment, StepResult, VirtualMachine};

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Player {
    One,
    Two,
}

impl Player {
    #[must_use]
    pub fn other(&self) -> Self {
        match self {
            Self::One => Self::Two,
            Self::Two => Self::One,
        }
    }

    #[must_use]
    pub fn numeric(&self) -> u8 {
        match self {
            Self::One => 1,
            Self::Two => 2,
        }
    }
}

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum SlotState {
    Token(Player),
    Empty,
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum PlacementResult {
    Success,
    InvalidColumn,
    ColumnFull,
    Connect4,
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct Board {
    slots: Vec<SlotState>,
    width: usize,
    height: usize,
}

impl Board {
    #[must_use]
    pub fn new_custom(width: usize, height: usize) -> Self {
        assert!(
            3 < width && width < 0x400 && 3 < height && height < 0x400,
            "{width}x{height} are silly dimensions!"
        );
        Self {
            slots: vec![SlotState::Empty; width * height],
            width,
            height,
        }
    }

    fn index(&self, x: usize, y: usize) -> usize {
        assert!(
            x < self.width && y < self.height,
            "({x}, {y}) out of bounds"
        );
        // Same "weird" order as in the data segment layout.
        x * self.height + y
    }

    #[must_use]
    pub fn get_width(&self) -> usize {
        self.width
    }

    #[must_use]
    pub fn get_height(&self) -> usize {
        self.height
    }

    #[must_use]
    pub fn get_slot(&self, x: usize, y: usize) -> SlotState {
        self.slots[self.index(x, y)]
    }

    fn count_towards(&self, x: usize, y: usize, dx: isize, dy: isize) -> usize {
        let expect_slot = self.get_slot(x, y);
        assert!(
            expect_slot != SlotState::Empty,
            "Counting from empty slot at ({x}, {y}) towards ({dx}, {dy})?!"
        );
        let mut streak = 0;
        for i in 1.. {
            let new_x = x as isize + i * dx;
            let new_y = y as isize + i * dy;
            if new_x < 0 || new_y < 0 {
                break;
            }
            let new_x = new_x as usize;
            let new_y = new_y as usize;
            if new_x >= self.width || new_y >= self.height {
                break;
            }
            if self.get_slot(new_x, new_y) != expect_slot {
                break;
            }
            streak += 1;
        }

        streak
    }

    fn have_connect4(&self, x: usize, y: usize) -> bool {
        assert!(
            x < self.width && y < self.height,
            "Checking connect4 at OOB ({x}, {y})?!"
        );
        for (dx, dy) in [(1, -1), (1, 0), (1, 1), (0, 1)] {
            let to_left = self.count_towards(x, y, -dx, -dy);
            let to_right = self.count_towards(x, y, dx, dy);
            if to_left + 1 + to_right >= 4 {
                return true;
            }
        }
        false
    }

    pub fn place_into_unsanitized_column(
        &mut self,
        column_index: u16,
        player: Player,
    ) -> PlacementResult {
        if column_index as usize >= self.width {
            return PlacementResult::InvalidColumn;
        }
        let x = column_index as usize;

        for y in 0..self.height {
            let slot_index = self.index(x, y);
            let slot = &mut self.slots[slot_index];
            if *slot == SlotState::Empty {
                *slot = SlotState::Token(player);
                if self.have_connect4(x, y) {
                    return PlacementResult::Connect4;
                }
                return PlacementResult::Success;
            }
        }

        PlacementResult::ColumnFull
    }

    fn encode_onto(&self, current_player: Player, segment: &mut Segment) {
        for (i, slot_state) in self.slots.iter().enumerate() {
            segment[i as u16] = match slot_state {
                SlotState::Empty => 0,
                SlotState::Token(token_player) if *token_player == current_player => 1,
                SlotState::Token(_) => 2,
            };
        }
    }

    #[must_use]
    pub fn is_full(&self) -> bool {
        // It's enough to check only the top row, since the rows below it have already been "filled up" before.
        for x in 0..self.width {
            if self.get_slot(x, self.height - 1) == SlotState::Empty {
                return false;
            }
        }
        true
    }
}

pub const DEFAULT_WIDTH: usize = 7;
pub const DEFAULT_HEIGHT: usize = 6;

impl Default for Board {
    fn default() -> Self {
        Self::new_custom(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    }
}

#[cfg(test)]
mod test_board {
    use super::*;

    #[test]
    fn test_default() {
        let b = Board::default();
        assert_eq!(b.get_width(), DEFAULT_WIDTH);
        assert_eq!(b.get_height(), DEFAULT_HEIGHT);
    }

    #[test]
    fn test_index() {
        let b = Board::default();
        assert_eq!(b.index(0, 0), 0);
        assert_eq!(b.index(1, 0), DEFAULT_HEIGHT);
        assert_eq!(b.index(0, 1), 1);
        assert_eq!(b.index(0, DEFAULT_HEIGHT - 1), DEFAULT_HEIGHT - 1);
        assert_eq!(b.index(1, DEFAULT_HEIGHT - 1), 2 * DEFAULT_HEIGHT - 1);
        assert_eq!(b.index(2, 0), 2 * DEFAULT_HEIGHT);
    }

    #[test]
    fn test_encoding_empty() {
        let segment_expect = Segment::new_zeroed();

        let mut segment_actual = Segment::new_zeroed();
        let b = Board::default();
        b.encode_onto(Player::One, &mut segment_actual);

        assert_eq!(segment_expect, segment_actual);
    }

    #[test]
    fn test_refuse_full() {
        let mut b = Board::default();

        for _ in 0..3 {
            let result = b.place_into_unsanitized_column(0, Player::One);
            assert_eq!(result, PlacementResult::Success);
            let result = b.place_into_unsanitized_column(0, Player::Two);
            assert_eq!(result, PlacementResult::Success);
        }

        let result = b.place_into_unsanitized_column(0, Player::One);
        assert_eq!(result, PlacementResult::ColumnFull);
    }

    #[test]
    fn test_refuse_invalid() {
        let mut b = Board::default();

        let result7 = b.place_into_unsanitized_column(7, Player::One);
        assert_eq!(result7, PlacementResult::InvalidColumn);

        let result8 = b.place_into_unsanitized_column(7, Player::One);
        assert_eq!(result8, PlacementResult::InvalidColumn);

        let result9999 = b.place_into_unsanitized_column(9999, Player::One);
        assert_eq!(result9999, PlacementResult::InvalidColumn);
    }

    #[test]
    fn test_encoding_simple() {
        let mut b = Board::default();
        let result = b.place_into_unsanitized_column(1, Player::One);
        assert_eq!(result, PlacementResult::Success);

        let mut segment_expect = Segment::new_zeroed();
        let mut segment_actual = Segment::new_zeroed();

        segment_expect[6] = 1;
        b.encode_onto(Player::One, &mut segment_actual);
        assert_eq!(segment_expect, segment_actual);

        segment_expect[6] = 2;
        b.encode_onto(Player::Two, &mut segment_actual);
        assert_eq!(segment_expect, segment_actual);
    }

    #[test]
    fn test_encoding_more() {
        let mut b = Board::default();
        let result = b.place_into_unsanitized_column(3, Player::One);
        assert_eq!(result, PlacementResult::Success);
        let result = b.place_into_unsanitized_column(4, Player::Two);
        assert_eq!(result, PlacementResult::Success);
        let result = b.place_into_unsanitized_column(4, Player::One);
        assert_eq!(result, PlacementResult::Success);

        let mut segment_expect = Segment::new_zeroed();
        let mut segment_actual = Segment::new_zeroed();

        segment_expect[18] = 1;
        segment_expect[24] = 2;
        segment_expect[25] = 1;
        b.encode_onto(Player::One, &mut segment_actual);
        assert_eq!(segment_expect, segment_actual);

        segment_expect[18] = 2;
        segment_expect[24] = 1;
        segment_expect[25] = 2;
        b.encode_onto(Player::Two, &mut segment_actual);
        assert_eq!(segment_expect, segment_actual);
    }

    fn assert_place_success(board: &mut Board, col: u16, player: Player) {
        assert_eq!(
            board.place_into_unsanitized_column(col, player),
            PlacementResult::Success
        );
    }

    #[test]
    fn test_full_board() {
        let mut b = Board::default();

        fn fill_column(col: u16, board: &mut Board, starting_with: Player) {
            assert_eq!(board.get_height(), 6);
            for _ in 0..3 {
                assert!(!board.is_full());
                assert_place_success(board, col, starting_with);
                assert!(!board.is_full());
                assert_place_success(board, col, starting_with.other());
            }
        }

        fill_column(0, &mut b, Player::One);
        fill_column(1, &mut b, Player::One);
        fill_column(2, &mut b, Player::One);
        // We start the middle column with the opposite player. This way, the "game" is guaranteed to be a draw.
        fill_column(3, &mut b, Player::Two);
        fill_column(4, &mut b, Player::One);
        fill_column(5, &mut b, Player::One);
        fill_column(6, &mut b, Player::One);

        assert!(b.is_full());
    }

    #[test]
    fn test_connect4_horizontal_negative() {
        let mut board = Board::default();

        assert_place_success(&mut board, 0, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 2, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 6, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 5, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 4, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 3, Player::One);
        assert!(!board.is_full());
    }

    #[test]
    fn test_connect4_horizontal_positive() {
        let mut board = Board::default();

        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 2, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 4, Player::Two);
        assert!(!board.is_full());
        assert_eq!(
            board.place_into_unsanitized_column(3, Player::Two),
            PlacementResult::Connect4
        );
    }

    #[test]
    fn test_connect4_vertical_positive() {
        let mut board = Board::default();

        assert_place_success(&mut board, 1, Player::One);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_eq!(
            board.place_into_unsanitized_column(1, Player::Two),
            PlacementResult::Connect4
        );
    }

    #[test]
    fn test_connect4_vertical_negative() {
        let mut board = Board::default();

        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::One);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert!(!board.is_full());
        assert_place_success(&mut board, 1, Player::Two);
        assert_eq!(
            board.place_into_unsanitized_column(1, Player::Two),
            PlacementResult::ColumnFull
        );
    }

    #[test]
    fn test_connect4_diag1_positive() {
        // TODO: Write a diag1 negative test.
        let mut board = Board::default();

        assert_place_success(&mut board, 2, Player::One);

        assert_place_success(&mut board, 3, Player::One);
        assert_place_success(&mut board, 3, Player::One);

        assert_place_success(&mut board, 4, Player::One);
        assert_place_success(&mut board, 4, Player::One);
        assert_place_success(&mut board, 4, Player::One);

        assert_place_success(&mut board, 2, Player::Two);
        assert_place_success(&mut board, 4, Player::Two);
        assert_place_success(&mut board, 3, Player::Two);
        assert_eq!(
            board.place_into_unsanitized_column(1, Player::Two),
            PlacementResult::Connect4
        );
    }

    #[test]
    fn test_connect4_diag2_positive() {
        // TODO: Write a diag2 negative test.
        let mut board = Board::default();

        assert_place_success(&mut board, 5, Player::One);

        assert_place_success(&mut board, 4, Player::One);
        assert_place_success(&mut board, 4, Player::One);

        assert_place_success(&mut board, 3, Player::One);
        assert_place_success(&mut board, 3, Player::One);
        assert_place_success(&mut board, 3, Player::One);

        assert_place_success(&mut board, 3, Player::Two);
        assert_place_success(&mut board, 4, Player::Two);
        assert_place_success(&mut board, 5, Player::Two);
        assert_eq!(
            board.place_into_unsanitized_column(6, Player::Two),
            PlacementResult::Connect4
        );
    }
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct PlayerData {
    instructions: Segment,
    data: Segment,
    last_move: u16,
    total_moves: u16,
    total_insns: u64,
}

pub const GAME_VERSION_MAJOR: u16 = 0x0001;
pub const GAME_VERSION_MINOR: u16 = 0x0000;

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum AlgorithmResult {
    Column(u16, bool),
    IllegalInstruction(u16),
    Timeout,
}

impl PlayerData {
    pub fn new(instructions: Segment) -> Self {
        Self {
            instructions,
            data: Segment::new_zeroed(),
            last_move: 0xFFFF,
            total_moves: 0,
            total_insns: 0,
        }
    }

    pub fn get_total_moves(&self) -> u16 {
        self.total_moves
    }

    pub fn get_total_insns(&self) -> u64 {
        self.total_insns
    }

    pub fn update_data(
        &mut self,
        own_identity: Player,
        max_steps: u64,
        board: &Board,
        other: &Self,
    ) {
        // https://github.com/BenWiederhake/tinyvm/blob/master/data-layout/connect4.md#data-segment-content-and-layout-for-connect4
        // - starting at 0x0000, size N words:
        //     * Contains the entire board.
        board.encode_onto(own_identity, &mut self.data);
        // - 0xFF80: Major version of the game and data: Must always be 0x0001, to distinguish it from other games. (In case someone wants to write a multi-game algorithm.)
        self.data[0xFF80] = GAME_VERSION_MAJOR;
        // - 0xFF81: Minor version of the game and data: Should be 0x0000 for the version in this document.
        self.data[0xFF81] = GAME_VERSION_MINOR;
        // - 0xFF82: Total time available for this move, in 4 words, most significant word first, similar to the returned value of the Time instruction.
        self.data[0xFF82] = (max_steps >> 48) as u16;
        self.data[0xFF83] = (max_steps >> 32) as u16;
        self.data[0xFF84] = (max_steps >> 16) as u16;
        self.data[0xFF85] = max_steps as u16;
        // - 0xFF86: Width of the board.
        self.data[0xFF86] = board.get_width() as u16;
        // - 0xFF87: Height of the board.
        self.data[0xFF87] = board.get_height() as u16;
        // - 0xFF88: Total number of moves made by the other player.
        self.data[0xFF88] = other.total_moves;
        // - 0xFF89: Total number of moves made by this player.
        self.data[0xFF89] = self.total_moves;
        // - 0xFF8A: Last move by other player. Again, 0-indexed. If this is the first move (and there is no previous move), this contains the value 0xFFFF.
        self.data[0xFF8A] = other.last_move;
        // - 0xFF8B-0xFFFF: These words may be overwritten arbitrarily on each turn by the game. If the game version is 0x0001.0x0000, then these words shall be overwritten with 0x0000.
        for i in 0xFF8B..=0xFFFF {
            self.data[i] = 0x0000;
        }
    }

    pub fn determine_answer(&mut self, max_steps: u64) -> AlgorithmResult {
        let mut vm = VirtualMachine::new(self.instructions.clone(), self.data.clone());
        for step in 0..max_steps {
            let last_step_result = vm.step();
            match last_step_result {
                StepResult::Continue | StepResult::DebugDump => {}
                StepResult::IllegalInstruction(insn) => {
                    self.total_insns += step + 1;
                    return AlgorithmResult::IllegalInstruction(insn);
                }
                StepResult::Return(column_index) => {
                    let deterministic = vm.was_deterministic_so_far();
                    self.data = vm.release_to_data_segment();
                    self.last_move = column_index;
                    self.total_moves += 1;
                    self.total_insns += step + 1;
                    return AlgorithmResult::Column(column_index, deterministic);
                }
            }
        }
        self.total_insns += max_steps;
        AlgorithmResult::Timeout
    }
}

#[cfg(test)]
mod test_player_data {
    use super::*;

    #[test]
    fn test_update_data() {
        let instructions = Segment::new_zeroed();
        let mut player_data = PlayerData::new(instructions);
        player_data.total_moves = 0x12;

        let mut b = Board::default();
        let result = b.place_into_unsanitized_column(3, Player::One);
        assert_eq!(result, PlacementResult::Success);
        let mut other_player_data = PlayerData::new(Segment::new_zeroed());
        other_player_data.total_moves = 0x34;

        player_data.update_data(Player::Two, 0x1234_5678_9ABC_DEF0, &b, &other_player_data);

        let data_segment = &player_data.data;
        assert_eq!(data_segment[0], 0);
        assert_eq!(data_segment[3 * 6 + 0], 2);
        assert_eq!(data_segment[3 * 6 + 1], 0);

        assert_eq!(data_segment[0x1234], 0);

        // - 0xFF80: Major version of the game and data: Must always be 0x0001, to distinguish it from other games. (In case someone wants to write a multi-game algorithm.)
        assert_eq!(data_segment[0xFF80], GAME_VERSION_MAJOR);
        // - 0xFF81: Minor version of the game and data: Should be 0x0000 for the version in this document.
        assert_eq!(data_segment[0xFF81], GAME_VERSION_MINOR);
        // - 0xFF82: Total time available for this move, in 4 words, most significant word first, similar to the returned value of the Time instruction.
        assert_eq!(data_segment[0xFF82], 0x1234);
        assert_eq!(data_segment[0xFF83], 0x5678);
        assert_eq!(data_segment[0xFF84], 0x9ABC);
        assert_eq!(data_segment[0xFF85], 0xDEF0);
        // - 0xFF86: Width of the board.
        assert_eq!(data_segment[0xFF86], DEFAULT_WIDTH as u16);
        // - 0xFF87: Height of the board.
        assert_eq!(data_segment[0xFF87], DEFAULT_HEIGHT as u16);
        // - 0xFF88: Total number of moves made by the other player.
        assert_eq!(data_segment[0xFF88], 0x34);
        // - 0xFF89: Total number of moves made by this player.
        assert_eq!(data_segment[0xFF89], 0x12);
        // - 0xFF8A: Last move by other player. Again, 0-indexed. If this is the first move (and there is no previous move), this contains the value 0xFFFF.
        assert_eq!(data_segment[0xFF8A], 0xFFFF);
        // - 0xFF8B-0xFFFF: These words may be overwritten arbitrarily on each turn by the game. If the game version is 0x0001.0x0000, then these words shall be overwritten with 0x0000.
        assert_eq!(data_segment[0xFFAB], 0x0000);
    }

    #[test]
    fn test_determine_answer() {
        let mut instructions = Segment::new_zeroed();
        instructions[0] = 0x3037; // ↓
        instructions[1] = 0x4013; // lw r0, 0x1337
        instructions[2] = 0x37CD; // ↓
        instructions[3] = 0x47AB; // lw r7, 0xABCD
        instructions[4] = 0x2077; // sw r7, r7
        instructions[5] = 0x102A; // ret
        let mut player_data = PlayerData::new(instructions);
        assert_eq!(player_data.last_move, 0xFFFF);
        assert_eq!(player_data.total_moves, 0);

        let result = player_data.determine_answer(0xFFFF);

        let data_segment = &player_data.data;
        assert_eq!(data_segment[0], 0);
        assert_eq!(data_segment[0xABCD], 0xABCD);
        assert_eq!(result, AlgorithmResult::Column(0x1337, true));
        assert_eq!(player_data.last_move, 0x1337);
        assert_eq!(player_data.total_moves, 1);
    }

    #[test]
    fn test_determine_answer_random() {
        let mut instructions = Segment::new_zeroed();
        instructions[0] = 0x3006; // lw r0, 6
        instructions[1] = 0x5E01; // rnd r1, r0
        instructions[2] = 0x102A; // ret
        let mut player_data = PlayerData::new(instructions);
        assert_eq!(player_data.last_move, 0xFFFF);
        assert_eq!(player_data.total_moves, 0);

        let result = player_data.determine_answer(0xFFFF);

        assert_eq!(result, AlgorithmResult::Column(6, false));
        assert_eq!(player_data.last_move, 6);
        assert_eq!(player_data.total_moves, 1);
    }
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum WinReason {
    Connect4,
    Timeout,
    IllegalInstruction(u16),
    IllegalColumn(u16),
    FullColumn(u16),
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum GameResult {
    Won(Player, WinReason),
    Draw,
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum GameState {
    RunningNextIs(Player),
    Ended(GameResult),
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct Game {
    player_one: PlayerData,
    player_two: PlayerData,
    board: Board,
    state: GameState,
    max_steps: u64,
    deterministic_so_far: bool,
    move_order: Vec<u8>,
}

impl Game {
    #[must_use]
    pub fn new(
        instructions_player_one: Segment,
        instructions_player_two: Segment,
        max_steps: u64,
    ) -> Self {
        Self {
            player_one: PlayerData::new(instructions_player_one),
            player_two: PlayerData::new(instructions_player_two),
            board: Board::default(),
            state: GameState::RunningNextIs(Player::One),
            max_steps,
            deterministic_so_far: true,
            move_order: Vec::with_capacity(DEFAULT_WIDTH * DEFAULT_HEIGHT),
        }
    }

    pub fn do_move(&mut self) {
        // Determine whose turn it is.
        let moving_player = match self.state {
            GameState::RunningNextIs(player) => player,
            GameState::Ended(_) => {
                return;
            }
        };
        let moving_player_data;
        let other_player_data;
        match moving_player {
            Player::One => {
                moving_player_data = &mut self.player_one;
                other_player_data = &mut self.player_two;
            }
            Player::Two => {
                moving_player_data = &mut self.player_two;
                other_player_data = &mut self.player_one;
            }
        }

        // Make a decision.
        moving_player_data.update_data(
            moving_player,
            self.max_steps,
            &self.board,
            other_player_data,
        );
        let step_result = moving_player_data.determine_answer(self.max_steps);
        let column_index = match step_result {
            AlgorithmResult::Column(column_index, deterministic_move) => {
                if !deterministic_move {
                    self.deterministic_so_far = false;
                }
                column_index
            }
            AlgorithmResult::IllegalInstruction(insn) => {
                // Loss by failure to produce a decision.
                self.state = GameState::Ended(GameResult::Won(
                    moving_player.other(),
                    WinReason::IllegalInstruction(insn),
                ));
                return;
            }
            AlgorithmResult::Timeout => {
                // Loss by failure to produce a decision.
                self.state =
                    GameState::Ended(GameResult::Won(moving_player.other(), WinReason::Timeout));
                return;
            }
        };

        // Do the move, check the result.
        let placement_result = // (force linebreak)
            self.board.place_into_unsanitized_column(column_index, moving_player);
        match placement_result {
            PlacementResult::Success => {
                self.move_order.push(column_index as u8);
            }
            PlacementResult::Connect4 => {
                self.move_order.push(column_index as u8);
                self.state = GameState::Ended(GameResult::Won(moving_player, WinReason::Connect4));
                return;
            }
            PlacementResult::InvalidColumn => {
                // Loss by invalid decision.
                self.state = GameState::Ended(GameResult::Won(
                    moving_player.other(),
                    WinReason::IllegalColumn(column_index),
                ));
                return;
            }
            PlacementResult::ColumnFull => {
                // Loss by invalid decision.
                self.state = GameState::Ended(GameResult::Won(
                    moving_player.other(),
                    WinReason::FullColumn(column_index),
                ));
                return;
            }
        }

        // Do we keep going?
        if self.board.is_full() {
            self.state = GameState::Ended(GameResult::Draw);
        } else {
            self.state = GameState::RunningNextIs(moving_player.other());
        }
    }

    pub fn conclude(&mut self) -> GameResult {
        loop {
            if let GameState::Ended(result) = self.state {
                return result;
            }
            self.do_move();
        }
    }

    #[must_use]
    pub fn get_state(&self) -> GameState {
        self.state
    }

    #[must_use]
    pub fn get_total_moves(&self) -> u16 {
        self.player_one.get_total_moves() + self.player_two.get_total_moves()
    }

    #[must_use]
    pub fn get_player_one_total_insn(&self) -> u64 {
        self.player_one.get_total_insns()
    }

    #[must_use]
    pub fn get_player_two_total_insn(&self) -> u64 {
        self.player_two.get_total_insns()
    }

    #[must_use]
    pub fn get_board(&self) -> &Board {
        &self.board
    }

    #[must_use]
    pub fn was_deterministic_so_far(&self) -> bool {
        self.deterministic_so_far
    }

    #[must_use]
    pub fn get_move_order(&self) -> &[u8] {
        &self.move_order
    }
}

#[cfg(test)]
mod test_game {
    use super::*;

    #[test]
    fn test_full_column() {
        let mut instructions = Segment::new_zeroed();
        instructions[0] = 0x102A; // ret
        let mut game = Game::new(instructions.clone(), instructions, 0x12345);
        assert!(game.was_deterministic_so_far());
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        game.do_move();
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::Two));
        game.do_move();
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        game.do_move();
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::Two));
        game.do_move();
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        game.do_move();
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::Two));

        assert_eq!(game.board.get_slot(0, 0), SlotState::Token(Player::One));
        assert_eq!(game.board.get_slot(0, 1), SlotState::Token(Player::Two));
        assert_eq!(game.board.get_slot(0, 2), SlotState::Token(Player::One));
        assert_eq!(game.board.get_slot(0, 3), SlotState::Token(Player::Two));
        assert_eq!(game.board.get_slot(0, 4), SlotState::Token(Player::One));
        assert_eq!(game.board.get_slot(0, 5), SlotState::Empty);

        game.do_move();
        assert_eq!(game.board.get_slot(0, 5), SlotState::Token(Player::Two));
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        // Next, player 1 attempts to insert into column 0, which is full,
        // therefore an illegal move, thus losing the game.
        game.do_move();
        assert_eq!(
            game.get_state(),
            GameState::Ended(GameResult::Won(Player::Two, WinReason::FullColumn(0)))
        );
        assert_eq!(game.get_move_order(), [0, 0, 0, 0, 0, 0]);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_illegal_column() {
        let mut instructions = Segment::new_zeroed();
        instructions[0] = 0x30FF; // lw r3, 0xFFFF
        instructions[1] = 0x102A; // ret
        let mut game = Game::new(instructions.clone(), instructions, 0x12345);
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        // Next, player 1 attempts to insert into column 0xFFFF, which is an invalid column,
        // thus losing the game.
        game.do_move();
        assert_eq!(
            game.get_state(),
            GameState::Ended(GameResult::Won(
                Player::Two,
                WinReason::IllegalColumn(0xFFFF)
            ))
        );

        // Test that do_move() is idempotent.
        game.do_move();
        assert_eq!(
            game.get_state(),
            GameState::Ended(GameResult::Won(
                Player::Two,
                WinReason::IllegalColumn(0xFFFF)
            ))
        );
        assert_eq!(game.get_move_order(), []);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_timeout() {
        let mut instructions = Segment::new_zeroed();
        instructions[0] = 0xB000; // j r0, +0x0000
        let mut game = Game::new(instructions.clone(), instructions, 123);
        assert_eq!(game.get_state(), GameState::RunningNextIs(Player::One));
        // Next, player 1 times out, thus losing the game.
        game.do_move();
        assert_eq!(
            game.get_state(),
            GameState::Ended(GameResult::Won(Player::Two, WinReason::Timeout))
        );
        assert_eq!(game.get_move_order(), []);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_two_illegal_column() {
        let mut instructions_one = Segment::new_zeroed();
        instructions_one[0] = 0x102A; // ret
        let mut instructions_two = Segment::new_zeroed();
        instructions_two[0] = 0x30FF; // lw r0, 0xFFFF
        instructions_two[1] = 0x102A; // ret
        let mut game = Game::new(instructions_one, instructions_two, 123);

        // Player 2 tries to play into an illegal column, losing the game.
        assert_eq!(
            game.conclude(),
            GameResult::Won(Player::One, WinReason::IllegalColumn(0xFFFF))
        );

        assert_eq!(game.player_one.total_moves, 1);
        assert_eq!(game.player_two.total_moves, 1);
        assert_eq!(game.get_move_order(), [0]);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_two_illegal_instruction() {
        let mut instructions_one = Segment::new_zeroed();
        instructions_one[0] = 0x102A; // ret
        let mut instructions_two = Segment::new_zeroed();
        instructions_two[0] = 0x0000; // ill 0x0000
        let mut game = Game::new(instructions_one, instructions_two, 123);

        // Player 2 terminates with an illegal instruction, losing the game.
        assert_eq!(
            game.conclude(),
            GameResult::Won(Player::One, WinReason::IllegalInstruction(0x0000))
        );

        assert_eq!(game.player_one.total_moves, 1);
        assert_eq!(game.player_two.total_moves, 0);
        assert_eq!(game.get_move_order(), [0]);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_connect4() {
        let mut instructions_one = Segment::new_zeroed();
        instructions_one[0] = 0x102A; // ret
        let mut instructions_two = Segment::new_zeroed();
        instructions_two[0] = 0x3001; // lw r0, 0x0001
        instructions_two[1] = 0x102A; // ret
        let mut game = Game::new(instructions_one, instructions_two, 123);

        // Player 1 finishes a connect4 in column 0.
        assert_eq!(
            game.conclude(),
            GameResult::Won(Player::One, WinReason::Connect4)
        );

        assert_eq!(game.player_one.total_moves, 4);
        assert_eq!(game.player_two.total_moves, 3);
        assert_eq!(game.get_move_order(), [0, 1, 0, 1, 0, 1, 0]);
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_board_full() {
        let mut instructions_one = Segment::new_zeroed();
        // On the nth move, place in column n % 7
        instructions_one[0] = 0x3189; // lw r1, 0xFF89
        instructions_one[1] = 0x2111; // lw r1, r1
        instructions_one[2] = 0x3007; // lw r0, 7
        instructions_one[3] = 0x6610; // modu r1 r0
        instructions_one[4] = 0x102A; // ret

        // Mark it read-only to prevent typos.
        let instructions_one = instructions_one;

        let mut instructions_two = Segment::new_zeroed();
        // Force the same pattern as in test_board::test_full_board.
        instructions_two[0] = 0x3189; // lw r1, 0xFF89
        instructions_two[1] = 0x2111; // lw r1, r1
        instructions_two[2] = 0x9101; // b r1 _move_nonzero # (offset is +0x3)
                                      // # .label _move_zero # On move 0, play in column 3.
        instructions_two[3] = 0x3003; // lw r0, 3
        instructions_two[4] = 0x102A; // ret
                                      // .label _move_nonzero
        instructions_two[5] = 0x3012; // lw r0, 18
        instructions_two[6] = 0x8610; // ge r1 r0
        instructions_two[7] = 0x9000; // b r0 _move_late # (offset is +0x2)
                                      // # .label _move_early # On moves 1-17, play in column (n - 1) % 7.
        instructions_two[8] = 0x5811; // decr r1
                                      // # j _move_late # Surprise optimization: This is a noop, this time!
                                      // .label _move_late # On moves 18-20, play in column n % 7.
        instructions_two[9] = 0x3007; // lw r0, 7
        instructions_two[10] = 0x6610; // modu r1 r0
        instructions_two[11] = 0x102A; // ret

        let mut game = Game::new(instructions_one, instructions_two, 123);

        // The board is full, thus the game is drawn.
        assert_eq!(game.conclude(), GameResult::Draw);

        assert_eq!(game.player_one.total_moves, 21);
        assert_eq!(game.player_two.total_moves, 21);
        assert_eq!(
            game.get_move_order(),
            [
                0, 3, 1, 0, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 0, 6, 1, 0, 2, 1, 3, 2, 4, 3, 5, 4, 6, 5,
                0, 6, 1, 0, 2, 1, 3, 2, 4, 4, 5, 5, 6, 6
            ]
        );
        assert!(game.was_deterministic_so_far());
    }

    #[test]
    fn test_two_random() {
        let mut instructions_one = Segment::new_zeroed();
        instructions_one[0] = 0x102A; // ret
        let mut instructions_two = Segment::new_zeroed();
        instructions_two[0] = 0x5E11; // rnd r1
        instructions_two[1] = 0x3001; // lw r0, 1
        instructions_two[2] = 0x102A; // ret
        let mut game = Game::new(instructions_one, instructions_two, 123);

        // Player 1 wins by connect 4.
        assert_eq!(
            game.conclude(),
            GameResult::Won(Player::One, WinReason::Connect4)
        );

        assert_eq!(game.player_one.total_moves, 4);
        assert_eq!(game.player_two.total_moves, 3);
        assert_eq!(game.get_move_order(), [0, 1, 0, 1, 0, 1, 0]);
        assert!(!game.was_deterministic_so_far());
    }
}
