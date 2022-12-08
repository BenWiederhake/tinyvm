extern crate getrandom;

use getrandom::getrandom;
use std::fmt::{Debug, Formatter, Result};
use std::ops::{Index, IndexMut};

#[derive(Debug)]
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

    fn step_binary(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
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
