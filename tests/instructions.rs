use tinyvm::{Segment, StepResult, VirtualMachine};

enum Expectation {
    ActualNumSteps(u64),
    Data(u16, u16),
    LastStep(StepResult),
    ProgramCounter(u16),
    Register(u16, u16),
}

fn segment_from_prefix(prefix: &[u16]) -> Segment {
    let mut segment = Segment::new_zeroed();
    for (i, &v) in prefix.iter().enumerate() {
        segment[i as u16] = v;
    }
    segment
}

fn run_test(
    instruction_prefix: &[u16],
    data_prefix: &[u16],
    max_steps: usize,
    expectations: &[Expectation],
) {
    let instruction_segment = segment_from_prefix(instruction_prefix);
    let data_segment = segment_from_prefix(data_prefix);

    let mut vm = VirtualMachine::new(instruction_segment, data_segment);

    let mut last_step_result = StepResult::Continue;
    let mut actual_steps = 0;

    for _ in 0..max_steps {
        last_step_result = vm.step();
        match last_step_result {
            StepResult::Continue => {}
            StepResult::DebugDump => {}
            StepResult::IllegalInstruction(_) => {
                break;
            }
            StepResult::Return(_) => {
                break;
            }
        }
        actual_steps += 1;
    }

    println!("VM state is {:?}", vm);
    println!("last_step_result is StepResult::{:?}", last_step_result);

    assert_eq!(actual_steps, vm.get_time());

    for expectation in expectations {
        match expectation {
            Expectation::ActualNumSteps(expected_steps) => {
                println!("Expecting {} actual steps", expected_steps);
                assert_eq!(*expected_steps, actual_steps);
            }
            Expectation::Data(address, expected_data) => {
                println!(
                    "Expecting word {:04X} at address {:04X}",
                    expected_data, address
                );
                assert_eq!(*expected_data, vm.get_data()[*address]);
            }
            Expectation::LastStep(expected_step_result) => {
                println!("Expecting last step to be {:?}", expected_step_result);
                assert_eq!(*expected_step_result, last_step_result);
            }
            Expectation::ProgramCounter(expected_pc) => {
                println!("Expecting pc to be {:?}", expected_pc);
                assert_eq!(*expected_pc, vm.get_program_counter());
            }
            Expectation::Register(register_index, expected_value) => {
                println!(
                    "Expecting register {} to contain {:04X}",
                    register_index, expected_value
                );
                assert_eq!(
                    *expected_value,
                    vm.get_registers()[*register_index as usize]
                );
            }
        }
    }
}

#[test]
fn test_null() {
    run_test(
        &[1, 2, 3],
        &[4, 5, 6],
        0,
        &[
            Expectation::ActualNumSteps(0),
            Expectation::Data(0, 4),
            Expectation::Data(1, 5),
            Expectation::Data(2, 6),
            Expectation::Data(3, 0),
            Expectation::Data(0xFFFE, 0),
            Expectation::Data(0xFFFF, 0),
            Expectation::LastStep(StepResult::Continue),
            Expectation::ProgramCounter(0),
            Expectation::Register(0, 0),
            Expectation::Register(1, 0),
            Expectation::Register(2, 0),
            Expectation::Register(3, 0),
            Expectation::Register(14, 0),
            Expectation::Register(15, 0),
        ],
    );
}

#[test]
fn test_illegal_zero() {
    run_test(
        &[0],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(0),
            Expectation::LastStep(StepResult::IllegalInstruction(0)),
            Expectation::ProgramCounter(0),
        ],
    );
}

#[test]
fn test_illegal_one() {
    run_test(
        &[0xFFFF],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(0),
            Expectation::LastStep(StepResult::IllegalInstruction(0xFFFF)),
            Expectation::ProgramCounter(0),
        ],
    );
}

#[test]
fn test_illegal_reserved() {
    run_test(
        &[0x0123],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(0),
            Expectation::LastStep(StepResult::IllegalInstruction(0x0123)),
            Expectation::ProgramCounter(0),
        ],
    );
}

#[test]
fn test_late_illegal() {
    run_test(
        &[0x3000, 0x0123],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::IllegalInstruction(0x0123)),
            Expectation::ProgramCounter(1),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x3xxx-load-immediate-low-sign-extended
// The instruction is `0b0011 0101 1000 1110`. Then this instruction will write the value 0xFF8E into register 5.
#[test]
fn test_load_imm_low_doc() {
    run_test(
        &[0x358E],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::Continue),
            Expectation::ProgramCounter(1),
            Expectation::Register(0, 0),
            Expectation::Register(5, 0xFF8E),
        ],
    );
}

#[test]
fn test_load_imm_low_simple() {
    run_test(
        &[0x3123],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::Continue),
            Expectation::ProgramCounter(1),
            Expectation::Register(0, 0),
            Expectation::Register(1, 0x0023),
        ],
    );
}

#[test]
fn test_return_simple() {
    run_test(
        &[0x102A],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(0),
            Expectation::ProgramCounter(0),
            Expectation::Register(0, 0),
            Expectation::LastStep(StepResult::Return(0x0000)),
        ],
    );
}

#[test]
// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102a-return
// The instruction is `0b0001 0000 0010 1010`, and register 0 contains the value 0x0042. Then this instruction will halt the machine, and present the value 0x0042 as the main result.
fn test_return_value() {
    run_test(
        &[0x3042, 0x102A],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(1),
            Expectation::Register(0, 0x0042),
            Expectation::LastStep(StepResult::Return(0x0042)),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102b-cpuid
// The instruction is `0b0001 0000 0010 1011`, and register 0 contains the value 0x0000. Then this instruction might, in a bare-bones and conforming VM, overwrite the register 0 with the value 0x8000, and registers 1, 2, and 3 each with the value 0x0000.
#[test]
fn test_cpuid_0() {
    run_test(
        &[0x102B],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(1),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x8000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0000),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102b-cpuid
// The instruction is `0b0001 0000 0010 1011`, register 0 contains the value 0x0007. Then this instruction should, in any VM without exotic extensions, overwrite the registers 0, 1, 2, and 3 each with the value 0x0000.
#[test]
fn test_cpuid_7() {
    run_test(
        &[0x3007, 0x102B],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(2),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0000),
        ],
    );
}

#[test]
fn test_cpuid_overwrite() {
    run_test(
        &[0x310A, 0x320B, 0x330C, 0x340D, 0x102B],
        &[],
        5,
        &[
            Expectation::ActualNumSteps(5),
            Expectation::ProgramCounter(5),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x8000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0000),
            Expectation::Register(4, 0x000D),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102c-debug-dump
// The instruction is `0b0001 0000 0010 1100`. Then memory and registers remain unchanged, and the program counter is incremented as usual. However, the caller of the VM may or may not decide to halt and inspect the VM, potentially resuming it later.
#[test]
fn test_debug_dump() {
    run_test(
        &[0x102C],
        &[4, 5, 6],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::Data(0, 4),
            Expectation::Data(1, 5),
            Expectation::Data(2, 6),
            Expectation::Data(3, 0),
            Expectation::Data(0xFFFE, 0),
            Expectation::Data(0xFFFF, 0),
            Expectation::LastStep(StepResult::DebugDump),
            Expectation::ProgramCounter(1),
            Expectation::Register(0, 0),
            Expectation::Register(1, 0),
            Expectation::Register(2, 0),
            Expectation::Register(3, 0),
            Expectation::Register(14, 0),
            Expectation::Register(15, 0),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x102d-time
// The instruction is `0b0001 0000 0010 1101`, and before this instruction, 7 instructions have already been executed. Then the registers 0, 1, 2, and 3 now contain the values 0x0000, 0x0000, 0x0000, and 0x0007, respectively.
#[test]
fn test_time_doc() {
    run_test(
        &[
            0x300A, 0x310B, 0x320C, 0x330D, 0x340E, 0x350F, 0x3609, 0x102D,
        ],
        &[],
        8,
        &[
            Expectation::ActualNumSteps(8),
            Expectation::ProgramCounter(8),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0007),
            Expectation::Register(4, 0x000E),
            Expectation::Register(5, 0x000F),
            Expectation::Register(6, 0x0009),
        ],
    );
}

#[test]
fn test_time_jump() {
    run_test(
        &[
            0xB005, // j r0 + 0x0005
            0,      // padding
            0,      // padding
            0,      // padding
            0,      // padding
            0x102D, // time
        ],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(6),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0001),
        ],
    );
}

#[test]
#[ignore = "write long-running program"]
fn test_time_long() {
    // FIXME: Test 'time' instruction with non-zero higher bytes!
    unimplemented!()
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x20xx-store-word-data
// The instruction is `0b0010 0000 0010 0101`, register 2 holds the value 0x1234, and register 5 holds the value 0x5678. Then this instruction will overwrite data memory at address 0x1234 with the value 0x5678.
#[test]
fn test_store_data_doc() {
    run_test(
        &[
            0x3234, 0x4212, // lw r2, 0x1234
            0x3578, 0x4556, // lw r5, 0x5678
            0x2025, // sw r2, r5
        ],
        &[],
        5,
        &[
            Expectation::ActualNumSteps(5),
            Expectation::ProgramCounter(5),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x1234),
            Expectation::Register(5, 0x5678),
            Expectation::Data(0x1234, 0x5678),
        ],
    );
}

#[test]
fn test_store_data_simple() {
    run_test(
        &[
            0x3245, // lw r2, 0x0045
            0x3567, // lw r5, 0x0067
            0x2025, // sw r2, r5
        ],
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(3),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x0045),
            Expectation::Register(5, 0x0067),
            Expectation::Data(0x0045, 0x0067),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x21xx-load-word-data
// The instruction is `0b0010 0001 0010 0101`, register 2 holds the value 0x1234, and data memory at address 0x1234 is 0x5678. Then this instruction will write the value 0x5678 into register 5.
#[test]
fn test_load_data_doc() {
    let mut initial_data = vec![0; 0x1234];
    initial_data.push(0x5678);
    run_test(
        &[
            0x3234, 0x4212, // lw r2, 0x1234
            0x2125, // lw r5, r2
        ],
        &initial_data,
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(3),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x1234),
            Expectation::Data(0x1234, 0x5678),
            Expectation::Register(5, 0x5678),
        ],
    );
}

#[test]
fn test_load_data_simple() {
    run_test(
        &[
            0x3205, // lw r2, 0x0005
            0x2125, // lw r5, r2
        ],
        &[0, 0, 0, 0, 0, 0xABCD],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(2),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x0005),
            Expectation::Data(0x0005, 0xABCD),
            Expectation::Register(5, 0xABCD),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x22xx-load-word-instruction
// The instruction is `0b0010 0010 0010 0101`, register 2 holds the value 0x1234, and instruction memory at address 0x1234 is 0x5678. Then this instruction will write the value 0x5678 into register 5.
#[test]
fn test_load_instruction_doc() {
    let mut initial_instructions = vec![
        0x3234, 0x4212, // lw r2, 0x1234
        0x2225, // lwi r5, r2
    ];
    while initial_instructions.len() < 0x1234 {
        initial_instructions.push(0);
    }
    initial_instructions.push(0x5678);
    run_test(
        &initial_instructions,
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(3),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x1234),
            Expectation::Data(0x1234, 0),
            Expectation::Register(5, 0x5678),
        ],
    );
}

#[test]
fn test_load_instruction_simple() {
    run_test(
        &[
            0x3205, // lw r2, 0x0005
            0x2225, // lwi r5, r2
            0, 0, 0, 0xABCD,
        ],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(2),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(2, 0x0005),
            Expectation::Data(0x0005, 0),
            Expectation::Register(5, 0xABCD),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x4xxx-load-immediate-high-only-high-byte
// The instruction is `0b0100 1010 0101 0110`, and register 10 contains the value 0x1234. Then this instruction will write the value 0x5634 into register 5.
#[test]
fn test_load_imm_high_doc_setup() {
    run_test(
        &[
            0x3A34, 0x4A12, // lw r10, 0x1234
        ],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(2),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(10, 0x1234),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x4xxx-load-immediate-high-only-high-byte
// The instruction is `0b0100 1010 0101 0110`, and register 10 contains the value 0x1234. Then this instruction will write the value 0x5634 into register 5.
#[test]
fn test_load_imm_high_doc() {
    run_test(
        &[
            0x3A34, 0x4A12, // lw r10, 0x1234
            0x4A56, // lhi r10, 0x5600
        ],
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(3),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(10, 0x5634),
        ],
    );
}

#[test]
fn test_load_imm_high_simple() {
    run_test(
        &[
            0x45AB, // lhi r5, 0xAB00
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(1),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(5, 0xAB00),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xbxxx-jump-to-register
// The instruction is `0b1011 0111 0011 0100`, and register 7 contains the value 0x1200. Then the program counter is updated to 0x1234.
#[test]
fn test_jump_register_doc1() {
    run_test(
        &[
            0x4712, // lhi r7, 0x1200
            0xB734, // j r7 + 0x0034
        ],
        &[],
        2,
        &[
            Expectation::Register(7, 0x1200),
            Expectation::ProgramCounter(0x1234),
            Expectation::ActualNumSteps(2),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xbxxx-jump-to-register
// The instruction is `0b1011 0111 1111 1111`, and register 7 contains the value 0x1234. Then the program counter is updated to 0x1233.
#[test]
fn test_jump_register_doc2() {
    run_test(
        &[
            0x3734, 0x4712, // lw r7, 0x1234
            0xB7FF, // j r7 - 0x0001
        ],
        &[],
        3,
        &[
            Expectation::Register(7, 0x1234),
            Expectation::ProgramCounter(0x1233),
            Expectation::ActualNumSteps(3),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_simple() {
    run_test(
        &[
            0xB042, // j r0 + 0x0042
        ],
        &[],
        1,
        &[
            Expectation::ProgramCounter(0x0042),
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_overflow() {
    run_test(
        &[
            0x37FF, 0x47FF, // lw r7, 0xFFFF
            0xB710, // j r7 + 0x0010
        ],
        &[],
        3,
        &[
            Expectation::Register(7, 0xFFFF),
            Expectation::ProgramCounter(0x000F),
            Expectation::ActualNumSteps(3),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_underflow() {
    run_test(
        &[
            0xB080, // j r0 - 0x0080
        ],
        &[],
        1,
        &[
            Expectation::ProgramCounter(0xFF80),
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_positive_imm() {
    run_test(
        &[
            0xB07F, // j r0 + 0x7F
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(0x007F),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_negative_imm() {
    run_test(
        &[
            0xB080, // j r0 - 0x80
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(0xFF80),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_positive() {
    run_test(
        &[
            0x37FF, 0x47FF, // lw r7, 0xFFFF
            0xB77F, // j r7 + 0x7F
        ],
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(0x007E),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_positive_nowrap() {
    run_test(
        &[
            0x37FF, 0x477F, // lw r7, 0x7FFF
            0xB77F, // j r7 + 0x7F
        ],
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(0x807E),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_negative() {
    run_test(
        &[
            0x37FF, 0x47FF, // lw r7, 0xFFFF
            0xB780, // j r7 - 0x80
        ],
        &[],
        3,
        &[
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(0xFF7F),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_register_extreme_negative_signedish() {
    run_test(
        &[
            0x4780, // lhi r7, 0x8000
            0xB780, // j r7 - 0x80
        ],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(0x7F80),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_program_counter_wraps() {
    let mut instructions = vec![0; 1 << 16];
    instructions[0x0000] = 0x37FF; // ↓
    instructions[0x0001] = 0x47FF; // lw r7, 0xFFFF
    instructions[0x0002] = 0xB700; // j r7 + 0x0000
    instructions[0xFFFF] = 0x3412; // lw r4, 0x0012
    run_test(
        &instructions,
        &[],
        4,
        &[
            Expectation::ActualNumSteps(4),
            Expectation::ProgramCounter(0x0000),
            Expectation::Register(7, 0xFFFF),
            Expectation::Register(4, 0x0012),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xaxxx-jump-by-immediate
// The program counter is 0x5000, the instruction at that address is `0b1010 0001 0010 0011`. Then the program counter is updated to 0x5000 + 2 + 0x0123 = 0x5125.
#[test]
fn test_jump_imm_doc1() {
    let mut instructions = vec![0; 1 << 16];
    instructions[0x0000] = 0x4350; // lhi r3, 0x5000
    instructions[0x0001] = 0xB300; // j r3 + 0x0000
    instructions[0x5000] = 0xA123; // j +0x125
    run_test(
        &instructions,
        &[],
        3,
        &[
            Expectation::Register(3, 0x5000),
            Expectation::ProgramCounter(0x5125),
            Expectation::ActualNumSteps(3),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0xaxxx-jump-by-immediate
// The program counter is 0x1234, the instruction at that address is `0b1010 1000 0000 0000`. Then the program counter is updated to 0x1233, i.e. the instruction before the jump.
#[test]
fn test_jump_imm_doc2() {
    let mut instructions = vec![0; 1 << 16];
    instructions[0x0000] = 0x4312; // lhi r3, 0x1200
    instructions[0x0001] = 0xB334; // j r3 + 0x0034
    instructions[0x1234] = 0xA800; // j -0x1
    run_test(
        &instructions,
        &[],
        3,
        &[
            Expectation::Register(3, 0x1200),
            Expectation::ProgramCounter(0x1233),
            Expectation::ActualNumSteps(3),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_immediate_overflow() {
    let mut instructions = vec![0; 1 << 16];
    instructions[0x0000] = 0x43FF; // lw r3, 0xFF00
    instructions[0x0001] = 0xB300; // j r3 + 0x0000
    instructions[0xFF00] = 0xA200; // j +0x202
    run_test(
        &instructions,
        &[],
        3,
        &[
            Expectation::Register(3, 0xFF00),
            Expectation::ActualNumSteps(3),
            Expectation::ProgramCounter(0x0102),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_immediate_underflow() {
    run_test(
        &[
            0xA830, // j -0x031
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(0xFFCF),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_immediate_extreme_positive() {
    run_test(
        &[
            0xA7FF, // j +0x801
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(0x0801),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_jump_immediate_extreme_negative() {
    run_test(
        &[
            0xAFFF, // j -0x800
        ],
        &[],
        1,
        &[
            Expectation::ActualNumSteps(1),
            Expectation::ProgramCounter(0xf800),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}
