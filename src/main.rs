// This lint could have been useful, but it generates too many false positives, so deactivate it:
#![allow(clippy::cast_possible_truncation)]

use std::fs;
use std::io::{Error, ErrorKind, Result};

use clap::Parser;

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Whether to run in general judgement mode
    #[arg(short, long)]
    judge: bool,

    /// One of more instruction segments (two for 'connect4' mode, two or more for 'judge' mode.)
    /// TODO: These bounds should be checked by clap.
    instruction_segments: Vec<String>,
}

use tinyvm::{Game, GameResult, Segment, WinReason};

fn parse_segment(segment_filename: &str) -> Result<Segment> {
    let segment_bytes = fs::read(segment_filename).map_err(|e| {
        Error::new(
            e.kind(),
            format!("Cannot read instruction segment from file {segment_filename}: {e}"),
        )
    })?;
    if segment_bytes.len() != (1 << 17) {
        return Err(Error::new(
            ErrorKind::InvalidData,
            format!(
                "{}: Wrong segment length, expected 131072, got {} instead.",
                segment_filename,
                segment_bytes.len()
            ),
        ));
    }

    let mut segment = Segment::new_zeroed();

    for i in 0..(1 << 16) {
        let byte_index = i * 2;
        let high_byte = u16::from(segment_bytes[byte_index]) << 8;
        let low_byte = u16::from(segment_bytes[byte_index + 1]);
        segment[i as u16] = high_byte | low_byte;
    }

    Ok(segment)
}

fn run_and_print_connect4_game(instructions_one: &Segment, instructions_two: &Segment) -> bool {
    let mut game = Game::new(instructions_one.clone(), instructions_two.clone(), 30_000);
    let result = game.conclude();
    print!("{{\"moves\": \"");
    for &col in game.get_move_order() {
        assert!(col < 10);
        print!("{col}");
    }
    print!("\", \"res\": {{");
    match result {
        GameResult::Draw => {
            print!("\"type\": \"draw\"");
        }
        GameResult::Won(player, reason) => {
            print!("\"type\": \"win\", \"by\": {}, ", player.numeric());
            let reason_text = match reason {
                WinReason::Connect4 => "connect4".into(),
                WinReason::Timeout => "timeout of the opponent".into(),
                WinReason::IllegalInstruction(insn) => {
                    format!("illegal instruction (0x{insn:04X}) of the opponent")
                }
                WinReason::IllegalColumn(col) => {
                    format!("opponent's attempt to move at non-existent column {col}")
                }
                WinReason::FullColumn(col) => {
                    format!("opponent's attempt to move at full column {col}")
                }
            };
            print!("\"reason\": \"{reason_text}\"");
        }
    }
    println!(
        "}}, \"times\": [{}, {}]}}",
        game.get_player_one_total_insn(),
        game.get_player_two_total_insn(),
    );
    game.was_deterministic_so_far()
}

fn run_and_print_many_connect4_games(instructions_one: &Segment, instructions_two: &Segment) {
    print!("[");
    let first_was_deterministic = run_and_print_connect4_game(instructions_one, instructions_two);
    if !first_was_deterministic {
        for _ in 0..999 {
            print!(",");
            let was_deterministic = run_and_print_connect4_game(instructions_one, instructions_two);
            assert!(!was_deterministic);
        }
    }
    println!("]");
}

fn main() -> Result<()> {
    let args = Args::parse();

    println!("args are: {args:?}");

    let segments = args
        .instruction_segments
        .iter()
        .map(|p| parse_segment(p))
        .collect::<Result<Vec<_>>>()?;

    if args.judge {
        assert!(
            segments.len() >= 2,
            "Wrong number of segments provided; TODO: should be checked by clap"
        );
        unimplemented!();
    } else {
        assert!(
            segments.len() == 2,
            "Wrong number of segments provided; TODO: should be checked by clap"
        );
        run_and_print_many_connect4_games(&segments[0], &segments[1]);
    }

    Ok(())
}
