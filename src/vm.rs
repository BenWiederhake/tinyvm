use getrandom::getrandom;
use std::fmt::{Debug, Formatter, Result};
use std::ops::{Index, IndexMut};

#[derive(Clone, PartialEq, Eq)]
pub struct Segment {
    backing: Box<[u16; 1 << 16]>,
}

impl Segment {
    #[must_use]
    pub fn new_zeroed() -> Segment {
        Segment {
            backing: Box::new([0; 1 << 16]),
        }
    }
}

impl Debug for Segment {
    fn fmt(&self, f: &mut Formatter) -> Result {
        f.write_str("Segment { backing: [")?;
        f.write_fmt(format_args!("{:04X}", self.backing[0]))?;
        // Invariant: Formatter is "always" dirently after a value or value-ish part.

        let mut last_word = self.backing[0];
        let mut repetitions = 0;

        fn append_value(f: &mut Formatter, word: u16) -> Result {
            f.write_fmt(format_args!(", {:04X}", word))
        }
        fn close_repetitions(f: &mut Formatter, last_word: u16, repetitions: usize) -> Result {
            if repetitions < 2 {
                for _ in 0..repetitions {
                    append_value(f, last_word)?;
                }
                Ok(())
            } else {
                f.write_fmt(format_args!(", <elided {} repetitions>", repetitions))
            }
        }

        for word in self.backing.iter().skip(1) {
            if *word == last_word {
                repetitions += 1;
            } else {
                close_repetitions(f, last_word, repetitions)?;
                repetitions = 0;
                append_value(f, *word)?;
                last_word = *word;
            }
        }
        close_repetitions(f, last_word, repetitions)?;

        f.write_str(" ] }")
    }
}

impl Index<u16> for Segment {
    type Output = u16;

    fn index(&self, index: u16) -> &Self::Output {
        &self.backing[index as usize]
    }
}

impl IndexMut<u16> for Segment {
    fn index_mut(&mut self, index: u16) -> &mut Self::Output {
        &mut self.backing[index as usize]
    }
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub enum StepResult {
    Continue,
    DebugDump,
    IllegalInstruction(u16),
    Return(u16),
}

impl Debug for StepResult {
    fn fmt(&self, f: &mut Formatter) -> Result {
        match self {
            StepResult::Continue => f.write_str("Continue"),
            StepResult::DebugDump => f.write_str("DebugDump"),
            StepResult::IllegalInstruction(insn) => {
                f.write_fmt(format_args!("IllegalInstruction(0x{:04x})", *insn))
            }
            StepResult::Return(value) => f.write_fmt(format_args!("Return(0x{:04x})", *value)),
        }
    }
}

fn random_upto_including(upper_bound: u16) -> u16 {
    let modulus = (upper_bound as u64) + 1;
    // Make a random u64, and do the modulo trick.
    // This *does* create a disparity in probabilities, but it's at most (2**16) / (2**64) = 3.55e-13,
    // so pretty darn unlikely to be noticed by anyone.
    let mut bytes = [0u8; 8];
    // If getrandom fails, tinyvm probably doesn't matter anymore. Crash and burn.
    getrandom(&mut bytes).expect("Cannot satisfy rnd instruction");
    let mut value: u64 = 0;
    value |= bytes[0] as u64;
    value <<= 8;
    value |= bytes[1] as u64;
    value <<= 8;
    value |= bytes[2] as u64;
    value <<= 8;
    value |= bytes[3] as u64;
    value <<= 8;
    value |= bytes[4] as u64;
    value <<= 8;
    value |= bytes[5] as u64;
    value <<= 8;
    value |= bytes[6] as u64;
    value <<= 8;
    value |= bytes[7] as u64;
    value <<= 8;
    value %= modulus;
    value as u16
}

#[derive(Debug)]
pub struct VirtualMachine {
    registers: [u16; 16],
    program_counter: u16,
    time: u64,
    instructions: Segment,
    data: Segment,
}

impl VirtualMachine {
    #[must_use]
    pub fn new(instructions: Segment, data: Segment) -> VirtualMachine {
        VirtualMachine {
            registers: [0; 16],
            program_counter: 0,
            time: 0,
            instructions,
            data,
        }
    }

    #[must_use]
    pub fn get_registers(&self) -> &[u16; 16] {
        &self.registers
    }

    pub fn set_register(&mut self, index: u16, value: u16) {
        self.registers[index as usize] = value;
    }

    #[must_use]
    pub fn get_program_counter(&self) -> u16 {
        self.program_counter
    }

    #[must_use]
    pub fn get_time(&self) -> u64 {
        self.time
    }

    #[must_use]
    pub fn get_instructions(&self) -> &Segment {
        &self.instructions
    }

    #[must_use]
    pub fn get_data(&self) -> &Segment {
        &self.data
    }

    #[must_use]
    pub fn release_to_data_segment(self) -> Segment {
        self.data
    }

    pub fn set_data_word(&mut self, index: u16, value: u16) {
        self.data[index] = value;
    }

    pub fn step(&mut self) -> StepResult {
        let instruction = self.instructions[self.program_counter];
        let mut increment_pc_as_usual = true;
        let step_result = match instruction & 0xF000 {
            // 0x0000 illegal
            0x1000 => self.step_special(instruction, &mut increment_pc_as_usual),
            0x2000 => self.step_memory(instruction),
            0x3000 => self.step_load_imm_low(instruction),
            0x4000 => self.step_load_imm_high(instruction),
            0x5000 => self.step_unary(instruction),
            0x6000 => self.step_binary(instruction),
            // 0x7000 illegal
            0x8000 => self.step_compare(instruction),
            0x9000 => self.step_branch(instruction, &mut increment_pc_as_usual),
            0xA000 => {
                increment_pc_as_usual = false;
                self.step_jump_imm(instruction)
            }
            0xB000 => {
                increment_pc_as_usual = false;
                self.step_jump_reg(instruction)
            }
            // 0xC000, 0xD000, 0xE000, 0xF000 illegal
            _ => {
                increment_pc_as_usual = false;
                StepResult::IllegalInstruction(instruction)
            }
        };
        if increment_pc_as_usual {
            self.program_counter = self.program_counter.wrapping_add(1);
        }
        match step_result {
            StepResult::Continue | StepResult::DebugDump => {
                self.time += 1;
            }
            _ => {}
        }

        step_result
    }

    fn step_special(&mut self, instruction: u16, increment_pc_as_usual: &mut bool) -> StepResult {
        if instruction & 0x0F00 != 0x0000 {
            return StepResult::IllegalInstruction(instruction);
        }

        match instruction & 0x00FF {
            0x2A => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102a-return
                // Return
                *increment_pc_as_usual = false;
                StepResult::Return(self.registers[0])
            }
            0x2B => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102b-cpuid
                // CPUID
                if self.registers[0] == 0x0000 {
                    self.registers[0] = 0x8000; // TODO: binary instructions for exponentiation and roots
                    self.registers[1] = 0x0000;
                    self.registers[2] = 0x0000;
                    self.registers[3] = 0x0000;
                } else {
                    self.registers[0] = 0x0000;
                    self.registers[1] = 0x0000;
                    self.registers[2] = 0x0000;
                    self.registers[3] = 0x0000;
                }
                StepResult::Continue
            }
            0x2C => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102c-debug-dump
                // Debug-dump
                StepResult::DebugDump
            }
            0x2D => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102d-time
                // Time
                self.registers[0] = (self.time >> 48) as u16;
                self.registers[1] = (self.time >> 32) as u16;
                self.registers[2] = (self.time >> 16) as u16;
                self.registers[3] = self.time as u16;
                StepResult::Continue
            }
            _ => StepResult::IllegalInstruction(instruction),
        }
    }

    fn step_memory(&mut self, instruction: u16) -> StepResult {
        let memory_command = (instruction & 0x0F00) >> 8;
        let register_address = (instruction & 0x00F0) >> 4;
        let register_data = instruction & 0x000F;
        let address = self.registers[register_address as usize];
        let value_in_register = &mut self.registers[register_data as usize];

        match memory_command {
            0 => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x20xx-store-word-data
                // Store word data
                self.data[address] = *value_in_register;
                StepResult::Continue
            }
            1 => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x21xx-load-word-data
                // Load word data
                *value_in_register = self.data[address];
                StepResult::Continue
            }
            2 => {
                // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x22xx-load-word-instruction
                // Load word instruction
                *value_in_register = self.instructions[address];
                StepResult::Continue
            }
            _ => StepResult::IllegalInstruction(instruction),
        }
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x3xxx-load-immediate-low-sign-extended
    fn step_load_imm_low(&mut self, instruction: u16) -> StepResult {
        let register = (instruction & 0x0F00) >> 8;
        let data = (instruction & 0x00FF) as i8 as i16 as u16; // sign-extend to 16 bits
        self.registers[register as usize] = data;
        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x4xxx-load-immediate-high-only-high-byte
    fn step_load_imm_high(&mut self, instruction: u16) -> StepResult {
        let register_index = (instruction & 0x0F00) >> 8;
        let register = &mut self.registers[register_index as usize];
        let data = (instruction & 0x00FF) << 8;
        *register &= 0x00FF;
        *register |= data;
        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x5xxx-unary-functions
    fn step_unary(&mut self, instruction: u16) -> StepResult {
        let function = (instruction & 0x0F00) >> 8;
        let source = self.registers[((instruction & 0x00F0) >> 4) as usize];
        let destination = &mut self.registers[(instruction & 0x000F) as usize];

        match function {
            0b1000 => {
                // * If FFFF=1000, the computed function is "decr" (add 1), e.g. decr(41) = 40
                *destination = source.wrapping_sub(1);
            }
            0b1001 => {
                // * If FFFF=1001, the computed function is "incr" (subtract 1), e.g. incr(41) = 42
                *destination = source.wrapping_add(1);
            }
            0b1010 => {
                // * If FFFF=1010, the computed function is "not" (bite-wise logical negation), e.g. not(0x1234) = 0xEDCB
                *destination = !source;
            }
            0b1011 => {
                // * If FFFF=1011, the computed function is "popcnt" (population count), e.g. popcnt(0xFFFF) = 16, popcnt(0x0000) = 0
                //     * Note that there are no silly exceptions as there would be in x86.
                *destination = source.count_ones() as u16;
            }
            0b1100 => {
                // * If FFFF=1100, the computed function is "clz" (count leading zeros), e.g. clz(0x8000) = 0, clz(0x0002) = 14
                *destination = source.leading_zeros() as u16;
            }
            0b1101 => {
                // * If FFFF=1101, the computed function is "ctz" (count trailing zeros), e.g. ctz(0x8000) = 15, ctz(0x0002) = 1
                *destination = source.trailing_zeros() as u16;
            }
            0b1110 => {
                // * If FFFF=1110, the computed function is "rnd" (random number up to AND INCLUDING), e.g. rnd(5) = 3, rnd(5) = 5, rnd(5) = 0
                //     * Note that rnd must never result in a value larger than the argument, so rnd(5) must never generate 6 or even 0xFFFF.
                *destination = random_upto_including(source);
            }
            0b1111 => {
                // * If FFFF=1111, the computed function is "mov" (move, identity function), e.g. mov(0x5678) = 0x5678
                *destination = source;
            }
            _ => {
                return StepResult::IllegalInstruction(instruction);
            }
        }

        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x6xxx-basic-binary-functions
    fn step_binary(&mut self, instruction: u16) -> StepResult {
        let function = (instruction & 0x0F00) >> 8;
        let source = self.registers[((instruction & 0x00F0) >> 4) as usize];
        let destination = &mut self.registers[(instruction & 0x000F) as usize];

        match function {
            0b0000 => {
                // * If FFFF=0000, the computed function is "add" (overflowing addition), e.g. fn(0x1234, 0xABCD) = 0xBE01
                //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
                *destination = source.wrapping_add(*destination);
            }
            0b0001 => {
                // * If FFFF=0001, the computed function is "sub" (overflowing subtraction), e.g. fn(0xBE01, 0xABCD) = 0x1234, fn(0x0007, 0x0009) = 0xFFFE
                //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
                *destination = source.wrapping_sub(*destination);
            }
            0b0010 => {
                // * If FFFF=0010, the computed function is "mul" (truncated multiplication, low word), e.g. fn(0x0005, 0x0007) = 0x0023, fn(0x1234, 0xABCD) = 0x4FA4
                //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
                *destination = source.wrapping_mul(*destination);
            }
            0b0011 => {
                // * If FFFF=0011, the computed function is "mulh" (truncated multiplication, high word), e.g. fn(0x0005, 0x0007) = 0x0000, fn(0x1234, 0xABCD) = 0x0C37
                //     * Note that there is no signed equivalent.
                let result = (source as u32) * (*destination as u32);
                *destination = (result >> 16) as u16;
            }
            0b0100 => {
                // * If FFFF=0100, the computed function is "div.u" (unsigned division, rounded towards 0), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0x0009
                //     * The result of dividing by zero is 0xFFFF, the highest unsigned value.
                *destination = source.checked_div(*destination).unwrap_or(0xFFFF);
            }
            0b0101 => {
                // * If FFFF=0101, the computed function is "div.s" (signed division, rounded towards 0), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0xFFFC
                //     * The result of dividing by zero is 0x7FFF, the highest signed value.
                //     * We define fn(0x8000, 0xFFFF) = 0x8000.

                if *destination == 0 {
                    *destination = 0x7FFF;
                } else {
                    *destination = (source as i16).wrapping_div(*destination as i16) as u16;
                }
            }
            0b0110 => {
                // * If FFFF=0110, the computed function is "mod.u" (unsigned modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x07F9
                //     * The result of modulo by zero is 0x0000.
                //     * Note that if x = div.u(a, b) and y = mod.u(a, b), then add(mul(x, b), y) will usually result in a.
                *destination = source.checked_rem(*destination).unwrap_or(0x0000);
            }
            0b0111 => {
                // * If FFFF=0111, the computed function is "mod.s" (signed modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x06D1
                //     * The result of modulo by zero is 0x0000.
                //     * Note that if x = div.s(a, b) and y = mod.s(a, b), then add(mul(x, b), y) will usually result in a.
                *destination = (source as i16)
                    .checked_rem(*destination as i16)
                    .unwrap_or(0x0000) as u16;
            }
            0b1000 => {
                // * If FFFF=1000, the computed function is "and" (bitwise and), e.g. fn(0x5500, 0x5050) = 0x5000
                *destination &= source;
            }
            0b1001 => {
                // * If FFFF=1001, the computed function is "or" (bitwise inclusive or), e.g. fn(0x5500, 0x5050) = 0x5550
                *destination |= source;
            }
            0b1010 => {
                // * If FFFF=1010, the computed function is "xor" (bitwise exclusive or), e.g. fn(0x5500, 0x5050) = 0x0550
                *destination ^= source;
            }
            0b1011 => {
                // * If FFFF=1011, the computed function is "sl" (bitshift left, filling the least-significant bits with zero), e.g. fn(0x1234, 0x0001) = 0x2468, fn(0xFFFF, 0x0010) = 0x0000
                //     * Note that there are no silly exceptions as there would be in x86.

                // And because of that weird exceptions, we can't just use '<<'.
                if *destination >= 16 {
                    *destination = 0;
                } else {
                    *destination = source.wrapping_shl(*destination as u32);
                }
            }
            0b1100 => {
                // * If FFFF=1100, the computed function is "srl" (logical bitshift right, filling the most significant bits with zero), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0x0000

                // '>>' would shift by (*destination & 0xF), which is not what we want. Therefore, do it manually:
                if *destination >= 16 {
                    *destination = 0;
                } else {
                    *destination = source.wrapping_shr(*destination as u32);
                }
            }
            0b1101 => {
                // * If FFFF=1101, the computed function is "sra" (arithmetic bitshift right, filling the most significant bits with the sign-bit), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0xFFFF

                // '>>' would shift by (*destination & 0xF), which is not what we want. Therefore, do it manually:
                if *destination >= 16 {
                    *destination = if source & 0x8000 != 0 { 0xFFFF } else { 0 };
                } else {
                    *destination = (source as i16).wrapping_shr(*destination as u32) as u16;
                }
            }
            _ => {
                return StepResult::IllegalInstruction(instruction);
            }
        }

        StepResult::Continue
    }

    fn step_compare(&mut self, instruction: u16) -> StepResult {
        let flag_l = (instruction & 0x0800) != 0;
        let flag_e = (instruction & 0x0400) != 0;
        let flag_g = (instruction & 0x0200) != 0;
        let flag_s = (instruction & 0x0100) != 0;
        let register_lhs = ((instruction & 0x00F0) >> 4) as usize;
        let register_rhs = (instruction & 0x000F) as usize;

        let (lhs, rhs) = if flag_s {
            // Sign-extend
            (
                self.registers[register_lhs] as i16 as i32,
                self.registers[register_rhs] as i16 as i32,
            )
        } else {
            // Zero-extend
            (
                self.registers[register_lhs] as u32 as i32,
                self.registers[register_rhs] as u32 as i32,
            )
        };

        self.registers[register_rhs] =
            ((flag_l && lhs < rhs) || (flag_e && lhs == rhs) || (flag_g && lhs > rhs)) as u16;
        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x9xxx-branch
    fn step_branch(&mut self, instruction: u16, increment_pc_as_usual: &mut bool) -> StepResult {
        let register = (instruction & 0x0F00) >> 8;
        if self.registers[register as usize] != 0 {
            *increment_pc_as_usual = false;
            let offset = (instruction & 0x007F) as i8 as i16 as u16; // sign-extend to 16 bits
            let sign_bit = instruction & 0x0080;
            if sign_bit == 0 {
                // - If S=0, the program counter is not incremented by 1 as usual, but rather incremented by 2 + 0b0VVVVVVV.
                self.program_counter = self.program_counter.wrapping_add(2 + offset);
            } else {
                // - If S=1, the program counter is not incremented by 1 as usual, but rather decremented by 1 + 0b0VVVVVVV.
                self.program_counter = self.program_counter.wrapping_sub(1 + offset);
            }
        }
        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xaxxx-jump-by-immediate
    fn step_jump_imm(&mut self, instruction: u16) -> StepResult {
        let offset = instruction & 0x07FF;
        let sign_bit = instruction & 0x0800;
        if sign_bit == 0 {
            // - If S=0, the program counter is not incremented by 1 as usual, but rather incremented by 2 + 0b0000 0VVV VVVV VVVV.
            self.program_counter = self.program_counter.wrapping_add(2 + offset);
        } else {
            // - If S=1, the program counter is not incremented by 1 as usual, but rather decremented by 1 + 0b0000 0VVV VVVV VVVV.
            self.program_counter = self.program_counter.wrapping_sub(1 + offset);
        }
        StepResult::Continue
    }

    // https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xbxxx-jump-to-register
    fn step_jump_reg(&mut self, instruction: u16) -> StepResult {
        let register = (instruction & 0x0F00) >> 8;
        let offset = (instruction & 0x00FF) as i8 as i16 as u16; // sign-extend to 16 bits
        self.program_counter = self.registers[register as usize].wrapping_add(offset);
        StepResult::Continue
    }
}
