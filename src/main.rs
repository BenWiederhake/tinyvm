// This lint could have been useful, but it generates too many false positives, so deactivate it:
#![allow(clippy::cast_possible_truncation)]

use std::fs;
use std::io::{Error, ErrorKind, Result};

use clap::{Parser, ValueEnum};

use tinyvm::connect4;
use tinyvm::test_driver;
use tinyvm::vm::Segment;

#[derive(Clone, Debug, Default, ValueEnum)]
enum RunnerType {
    #[default]
    Connect4,
    Judge,
    // FIXME: Also permit "test_driver"
    TestDriver,
}

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Args {
    /// Which type of execution environment to use.
    #[arg(short, long, value_enum, default_value_t)]
    mode: RunnerType,

    /// One of more instruction segments (two for 'connect4' mode, two or more for 'judge' mode.)
    /// TODO: These bounds should be checked by clap.
    instruction_segments: Vec<String>,
}

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

fn main() -> Result<()> {
    let args = Args::parse();

    let segments = args
        .instruction_segments
        .iter()
        .map(|p| parse_segment(p))
        .collect::<Result<Vec<_>>>()?;

    match args.mode {
        RunnerType::Connect4 => {
            assert!(
                segments.len() == 2,
                "Wrong number of segments provided; TODO: should be checked by clap"
            );
            // TODO: Make the budget per move configurable through the CLI?
            connect4::run_and_print_many_games(&segments[0], &segments[1]);
        }
        RunnerType::Judge => {
            assert!(
                segments.len() >= 2,
                "Wrong number of segments provided; TODO: should be checked by clap"
            );
            unimplemented!();
        }
        RunnerType::TestDriver => {
            assert!(
                segments.len() == 2,
                "Wrong number of segments provided; TODO: should be checked by clap"
            );
            let total_budget = 30_000; // TODO: make it configurable through CLI
            test_driver::run_and_print_tests(&segments[0], &segments[1], total_budget);
        }
    }

    Ok(())
}
