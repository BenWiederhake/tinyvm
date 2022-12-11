mod connect4;
mod vm;

pub use connect4::{
    AlgorithmResult, Board, Game, GameResult, GameState, Player, SlotState, WinReason,
};
pub use vm::{Segment, StepResult, VirtualMachine};
