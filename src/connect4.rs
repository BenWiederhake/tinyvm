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
