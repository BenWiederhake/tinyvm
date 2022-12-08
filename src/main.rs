use std::io::{Error, ErrorKind, Result};
use std::{env, fs, process};

use tinyvm::{Segment, VirtualMachine};

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
            "USAGE: {} /path/to/vm_instruction_segment /path/to/vm_data_segment",
            args[0]
        );
        process::exit(1);
    }

    let instruction_segment_bytes = fs::read(args[1].clone())?;
    let data_segment_bytes = fs::read(args[2].clone())?;

    Ok((
        parse_segment(&instruction_segment_bytes, "instruction")?,
        parse_segment(&data_segment_bytes, "data")?,
    ))
}

fn main() -> Result<()> {
    let (instruction_segment, data_segment) = parse_args()?;
    let mut vm = VirtualMachine::new(instruction_segment, data_segment);
    println!("First step result is {:?}", vm.step());

    Ok(())
}
