use crate::vm::{Segment, StepResult, VirtualMachine};

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Player {
    One,
    Two,
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
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct Board {
    slots: Vec<SlotState>,
    width: usize,
    height: usize,
}

impl Board {
    pub fn new_custom(width: usize, height: usize) -> Board {
        assert!(
            3 < width && width < 0x400 && 3 < height && height < 0x400,
            "{}x{} are silly dimensions!",
            width,
            height
        );
        Board {
            slots: vec![SlotState::Empty; width * height],
            width,
            height,
        }
    }

    fn index(&self, x: usize, y: usize) -> usize {
        assert!(
            x < self.width && y < self.height,
            "({}, {}) out of bounds",
            x,
            y
        );
        // Same "weird" order as in the data segment layout.
        x * self.height + y
    }

    pub fn get_width(&self) -> usize {
        self.width
    }

    pub fn get_height(&self) -> usize {
        self.height
    }

    pub fn get_slot(&self, x: usize, y: usize) -> SlotState {
        self.slots[self.index(x, y)]
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
}

pub const DEFAULT_WIDTH: usize = 7;
pub const DEFAULT_HEIGHT: usize = 6;

impl Default for Board {
    fn default() -> Board {
        Board::new_custom(DEFAULT_WIDTH, DEFAULT_HEIGHT)
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

        for _ in 0..6 {
            let result = b.place_into_unsanitized_column(0, Player::One);
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
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct PlayerData {
    instructions: Segment,
    data: Segment,
    last_move: u16,
    total_moves: u16,
}

pub const GAME_VERSION_MAJOR: u16 = 0x0001;
pub const GAME_VERSION_MINOR: u16 = 0x0000;

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum AlgorithmResult {
    Column(u16),
    IllegalInstruction(u16),
    Timeout,
}

impl PlayerData {
    pub fn new(instructions: Segment) -> PlayerData {
        PlayerData {
            instructions,
            data: Segment::new_zeroed(),
            last_move: 0xFFFF,
            total_moves: 0,
        }
    }

    pub fn get_last_move(&self) -> u16 {
        self.last_move
    }

    pub fn get_total_moves(&self) -> u16 {
        self.total_moves
    }

    pub fn update_data(
        &mut self,
        own_identity: Player,
        max_steps: u64,
        board: &Board,
        other: &PlayerData,
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
        for _ in 0..max_steps {
            let last_step_result = vm.step();
            match last_step_result {
                StepResult::Continue => {}
                StepResult::DebugDump => {}
                StepResult::IllegalInstruction(insn) => {
                    return AlgorithmResult::IllegalInstruction(insn);
                }
                StepResult::Return(column_index) => {
                    self.data = vm.release_to_data_segment();
                    self.last_move = column_index;
                    self.total_moves += 1;
                    return AlgorithmResult::Column(column_index);
                }
            }
        }
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

        player_data.update_data(Player::Two, 0x123456789ABCDEF0, &b, &other_player_data);

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
        assert_eq!(result, AlgorithmResult::Column(0x1337));
        assert_eq!(player_data.last_move, 0x1337);
        assert_eq!(player_data.total_moves, 1);
    }
}
