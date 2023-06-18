use std::io::{Error, ErrorKind, Result};
use std::{env, fs, process};

use tinyvm::{Game, GameResult, Segment, WinReason};

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

fn run_and_print_game(instructions_one: &Segment, instructions_two: &Segment) -> Result<bool> {
    let mut game = Game::new(
        instructions_one.clone(),
        instructions_two.clone(),
        1_000_000,
    );
    let result = game.conclude();
    print!(
        "{{\"det\": {}, \"moves\": \"",
        game.was_deterministic_so_far()
    );
    for &col in game.get_move_order() {
        assert!(col < 10);
        print!("{}", col);
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
                    format!("illegal instruction (0x{:04X}) of the opponent", insn)
                }
                WinReason::IllegalColumn(col) => {
                    format!("opponent's attempt to move at non-existent column {}", col)
                }
                WinReason::FullColumn(col) => {
                    format!("opponent's attempt to move at full column {}", col)
                }
            };
            print!("\"reason\": \"{}\"", reason_text);
        }
    }
    println!(
        "}}, \"times\": [{}, {}]}}",
        game.get_player_one_total_insn(),
        game.get_player_two_total_insn(),
    );
    return Ok(game.was_deterministic_so_far());
}

fn main() -> Result<()> {
    let (instructions_one, instructions_two) = parse_args()?;

    print!("[");
    let first_was_deterministic = run_and_print_game(&instructions_one, &instructions_two)?;
    if !first_was_deterministic {
        for _ in 0..99 {
            print!(",");
            let was_deterministic = run_and_print_game(&instructions_one, &instructions_two)?;
            assert!(!was_deterministic);
        }
    }
    println!("]");

    Ok(())
}
