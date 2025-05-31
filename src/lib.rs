// This lints could have been useful, but they generate tons of false positives, so deactivate them:
#![allow(clippy::cast_possible_truncation)]
#![allow(clippy::cast_possible_wrap)]
#![allow(clippy::cast_sign_loss)]
// This lint makes useless suggestions.
#![allow(clippy::missing_const_for_fn)]

#[macro_use]
extern crate lazy_static;

pub mod connect4;
pub mod test_driver;
pub mod vm;
