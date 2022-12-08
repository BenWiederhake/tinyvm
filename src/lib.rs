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

#[derive(Debug)]
pub struct VirtualMachine {
    registers: [u16; 16],
    program_counter: u16,
    instructions: Segment,
    data: Segment,
}

impl VirtualMachine {
    #[must_use]
    pub fn new(instructions: Segment, data: Segment) -> VirtualMachine {
        VirtualMachine {
            registers: [0; 16],
            program_counter: 0,
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
            self.program_counter += 1;
        }
        step_result
    }

    fn step_special(&mut self, instruction: u16, increment_pc_as_usual: &mut bool) -> StepResult {
        unimplemented!()
    }

    fn step_memory(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_load_imm_low(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_load_imm_high(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_unary(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_binary(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_compare(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_branch(&mut self, instruction: u16, increment_pc_as_usual: &mut bool) -> StepResult {
        unimplemented!()
    }

    fn step_jump_imm(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }

    fn step_jump_reg(&mut self, instruction: u16) -> StepResult {
        unimplemented!()
    }
}
