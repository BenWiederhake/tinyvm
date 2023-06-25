// This lints could have been useful, but they generate tons of false positives, so deactivate them:
#![allow(clippy::cast_possible_truncation)]
#![allow(clippy::cast_possible_wrap)]
#![allow(clippy::cast_sign_loss)]
// This lint makes useless suggestions.
#![allow(clippy::missing_const_for_fn)]

#[macro_use]
extern crate lazy_static;

mod connect4;
mod vm;

pub use connect4::{
    AlgorithmResult, Board, Game, GameResult, GameState, Player, SlotState, WinReason,
};
pub use vm::{Segment, StepResult, VirtualMachine};
