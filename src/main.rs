use std::io::{Error, ErrorKind, Result};
use std::{env, fs, process};

use tinyvm::{Game, GameResult, Player, Segment, SlotState, WinReason};

fn parse_segment(segment_bytes: &[u8], segment_type: &str) -> Result<Segment> {
    if segment_bytes.len() != (1 << 17) {
        return Err(Error::new(
            ErrorKind::InvalidData,
            format!(
                "Wrong {} segment length, expected 131072, got {} instead.",
                segment_type,
                segment_bytes.len()
            ),
        ));
    }

    let mut segment = Segment::new_zeroed();

    for i in 0..(1 << 16) {
        let byte_index = i * 2;
        let high_byte = (segment_bytes[byte_index] as u16) << 8;
        let low_byte = segment_bytes[byte_index + 1] as u16;
        segment[i as u16] = high_byte | low_byte;
    }

    Ok(segment)
}

fn parse_args() -> Result<(Segment, Segment)> {
    let args = env::args().collect::<Vec<_>>();
    if args.len() != 3 {
        eprintln!(
            "USAGE: {} /path/to/instruction_segment_player_one /path/to/instruction_segment_player_two",
            args[0]
        );
        process::exit(1);
    }

    let instructions_one_bytes = fs::read(args[1].clone())?;
    let instructions_two_bytes = fs::read(args[2].clone())?;

    Ok((
        parse_segment(&instructions_one_bytes, "player one instruction")?,
        parse_segment(&instructions_two_bytes, "player two instruction")?,
    ))
}

fn main() -> Result<()> {
    let (instructions_one, instructions_two) = parse_args()?;
    println!("Player one: {:?}", &instructions_one);
    println!("Player two: {:?}", &instructions_two);
    let mut game = Game::new(instructions_one, instructions_two, 10_000_000);

    let result = game.conclude();

    let result_text = match result {
        GameResult::Draw => "The game was drawn".into(),
        GameResult::Won(player, reason) => {
            let player_name = match player {
                Player::One => "1",
                Player::Two => "2",
            };
            let reason_text = match reason {
                WinReason::Connect4 => "by connect4".into(),
                WinReason::Timeout => "by timeout of the opponent".into(),
                WinReason::IllegalInstruction(insn) => {
                    format!("by illegal instruction (0x{:04X}) of the opponent", insn)
                }
                WinReason::IllegalColumn(col) => format!(
                    "by opponent's attempt to move at non-existent column {}",
                    col
                ),
                WinReason::FullColumn(col) => {
                    format!("by opponent's attempt to move at full column {}", col)
                }
            };
            format!("Player {} won {}", player_name, reason_text)
        }
    };
    println!("{} after {} moves.", result_text, game.get_total_moves());
    println!("End result (1=x, 2=O):");
    let board = game.get_board();
    for y in (0..board.get_height()).rev() {
        print!("|");
        for x in 0..board.get_width() {
            let symbol = match board.get_slot(x, y) {
                SlotState::Empty => "_",
                SlotState::Token(Player::One) => "x",
                SlotState::Token(Player::Two) => "O",
            };
            print!(" {}", symbol);
        }
        println!(" |");
    }
    print!("+");
    for _ in 0..board.get_width() {
        print!("--");
    }
    println!("-+");

    Ok(())
}
