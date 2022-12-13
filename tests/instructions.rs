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
        if actual_steps % 0x100_0000 == 0 {
            println!(
                "Intermediate state: registers={:?}, pc={:04X}, actual_steps={}",
                vm.get_registers(),
                vm.get_program_counter(),
                actual_steps
            );
        }
    }

    println!("Data segment: {:?}", vm.get_data());
    println!(
        "Final state: registers={:?}, pc={:04X}, actual_steps={}",
        vm.get_registers(),
        vm.get_program_counter(),
        actual_steps
    );
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
fn test_time_long() {
    run_test(
        &[
            0x37AB, // lw r7, 0xFFAB
            0x5877, // decr r7
            0x9780, // b r7 -0x1
            0x102D, // time
            0x102A, // ret
        ],
        &[],
        0xF_FFFF, // More than enough; definitely not tight
        &[
            Expectation::ActualNumSteps(1 + 2 * 0xFFAB + 1),
            Expectation::ProgramCounter(4),
            Expectation::LastStep(StepResult::Return(0)),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0001),
            Expectation::Register(3, 1 + 2 * 0x7FAB),
        ],
    );
}

#[test]
#[ignore = "Test takes too long"]
// Runs in 122.29s in debug mode, that's about 35 MHz in simulation. Whoa!
// Runs in 14.67s in release mode, that's about 292 MHz in simulation. Very whoa!
fn test_time_very_long() {
    #[rustfmt::skip] // Would break the labels. See https://github.com/rust-lang/rustfmt/issues/5630
    run_test(
        &[
            0x3705, 0x47B5, // lw r7, 0xB505 // executed 1 time
            0x5F71, // mv r1, r7 // executed 1 time
                    // .label outer_loop
            0x5F72, // mv r2, r7 // executed 0xB505 times
                    // .label inner_loop
            0x5822, // decr r2 // executed 0xB505 * 0xB505 times
            0x9280, // b r2 inner_loop // (offset is -0x1) // executed 0xB505 * 0xB505 times
            0x5811, // decr r1 // executed 0xB505 times
            0x9183, // b r1 outer_loop // (offset is -0x4) // executed 0xB505 times
            0x102D, // time // executed 0 times or 1 time, depending on how you look at it
            0x102A, // ret // executed 0 times
            // Total steps: (3 or 4) + 3 * 0xB505 + 2 * 0xB505 * 0xB505 = 0x100024344 or 0x100024345
        ],
        &[],
        0x1_FFFF_FFFF, // More than enough; definitely not tight
        &[
            Expectation::ActualNumSteps(0x100024345),
            Expectation::ProgramCounter(9),
            Expectation::LastStep(StepResult::Return(0)),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0001),
            Expectation::Register(2, 0x0002),
            Expectation::Register(3, 0x4344),
        ],
    );
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

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x9xxx-branch
// The program counter is 0x1234, the instruction at that address is `0b1001 0011 1000 0000`, and register 3 contains the value 0x0001. Because 0x0001 is considered true, the program counter is then updated to 0x1233, i.e. the instruction before the branch.
#[test]
fn test_branch_doc1() {
    let mut instructions = vec![0; 1 << 16];
    instructions[0x0000] = 0x3301; // lw r3, 0x0001
    instructions[0x0001] = 0x4712; // lhi r7, 0x1200
    instructions[0x0002] = 0xB734; // j r7 + 0x0034
    instructions[0x1234] = 0x9380; // b r3 -0x1
    run_test(
        &instructions,
        &[],
        4,
        &[
            Expectation::Register(3, 0x0001),
            Expectation::Register(7, 0x1200),
            Expectation::ProgramCounter(0x1233),
            Expectation::ActualNumSteps(4),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x9xxx-branch
// The instruction is `0b1001 0101 1000 0000`, and register 5 contains the value 0x0000. Because 0x0000 is considered false, the program counter is incremented as normal.
#[test]
fn test_branch_doc2() {
    run_test(
        &[
            0x9580, // b r5 -0x1
        ],
        &[],
        1,
        &[
            Expectation::Register(5, 0),
            Expectation::ProgramCounter(1),
            Expectation::ActualNumSteps(1),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x8xxx-compare
// The instruction is `0b1000 1010 0011 0100`, register 3 contains the value 0x0005, and register 4 contains the value 0x0007. Then this instruction will write the value 0x0001 into register 4, because 5 is not equal 7.
#[test]
fn test_compare_doc() {
    run_test(
        &[
            0x3305, // lw r3, 0x0005
            0x3407, // lw r4, 0x0007
            0x8A34, // ne r4, r3 (or cmp.lg r4, r3)
        ],
        &[],
        3,
        &[
            Expectation::Register(3, 5),
            Expectation::ProgramCounter(3),
            Expectation::ActualNumSteps(3),
            Expectation::Register(4, 1),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

fn run_compare_test(a: u16, b: u16, flags: u16, result: u16) {
    run_test(
        &[
            0x3100 | (a & 0xFF),        // ↓
            0x4100 | ((a >> 8) & 0xFF), // lw r1, a
            0x3200 | (b & 0xFF),        // ↓
            0x4200 | ((b >> 8) & 0xFF), // lw r2, b
            0x8012 | (flags << 8),      // cmp.flags r2, r1
        ],
        &[],
        5,
        &[
            Expectation::ProgramCounter(5),
            Expectation::ActualNumSteps(5),
            Expectation::Register(1, a),
            Expectation::Register(2, result),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_compare_false1() {
    run_compare_test(3, 4, 0b0000, 0);
    run_compare_test(3, 4, 0b0001, 0);
}

#[test]
fn test_compare_false2() {
    run_compare_test(7, 7, 0b0000, 0);
    run_compare_test(7, 7, 0b0001, 0);
}

#[test]
fn test_compare_false3() {
    run_compare_test(8, 1, 0b0000, 0);
    run_compare_test(8, 1, 0b0001, 0);
}

#[test]
fn test_compare_less_positive() {
    run_compare_test(5, 7, 0b1000, 1);
    run_compare_test(5, 7, 0b1001, 1);
}

#[test]
fn test_compare_less_negative1() {
    run_compare_test(7, 7, 0b1000, 0);
    run_compare_test(7, 7, 0b1001, 0);
}

#[test]
fn test_compare_less_negative2() {
    run_compare_test(9, 7, 0b1000, 0);
    run_compare_test(9, 7, 0b1001, 0);
}

#[test]
fn test_compare_equal_positive() {
    run_compare_test(6, 6, 0b0100, 1);
    run_compare_test(6, 6, 0b0101, 1);
}

#[test]
fn test_compare_equal_negative1() {
    run_compare_test(9, 6, 0b0100, 0);
    run_compare_test(9, 6, 0b0101, 0);
}

#[test]
fn test_compare_equal_negative2() {
    run_compare_test(6, 9, 0b0100, 0);
    run_compare_test(6, 9, 0b0101, 0);
}

#[test]
fn test_compare_lessequal_positive1() {
    run_compare_test(7, 8, 0b1100, 1);
    run_compare_test(7, 8, 0b1101, 1);
}

#[test]
fn test_compare_lessequal_positive2() {
    run_compare_test(7, 7, 0b1100, 1);
    run_compare_test(7, 7, 0b1101, 1);
}

#[test]
fn test_compare_lessequal_negative() {
    run_compare_test(8, 7, 0b1100, 0);
    run_compare_test(8, 7, 0b1101, 0);
}

#[test]
fn test_compare_greater_positive() {
    run_compare_test(8, 2, 0b0010, 1);
    run_compare_test(8, 2, 0b0011, 1);
}

#[test]
fn test_compare_greater_negative1() {
    run_compare_test(3, 9, 0b0010, 0);
    run_compare_test(3, 9, 0b0011, 0);
}

#[test]
fn test_compare_greater_negative2() {
    run_compare_test(9, 9, 0b0010, 0);
    run_compare_test(9, 9, 0b0011, 0);
}

#[test]
fn test_compare_lessgreater_positive1() {
    run_compare_test(1, 9, 0b1010, 1);
    run_compare_test(1, 9, 0b1011, 1);
}

#[test]
fn test_compare_lessgreater_positive2() {
    run_compare_test(9, 1, 0b1010, 1);
    run_compare_test(9, 1, 0b1011, 1);
}

#[test]
fn test_compare_lessgreater_negative() {
    run_compare_test(9, 9, 0b1010, 0);
    run_compare_test(9, 9, 0b1011, 0);
}

#[test]
fn test_compare_equalgreater_positive1() {
    run_compare_test(2, 2, 0b0110, 1);
    run_compare_test(2, 2, 0b0111, 1);
}

#[test]
fn test_compare_equalgreater_positive2() {
    run_compare_test(5, 2, 0b0110, 1);
    run_compare_test(5, 2, 0b0111, 1);
}

#[test]
fn test_compare_equalgreater_negative() {
    run_compare_test(1, 2, 0b0110, 0);
    run_compare_test(1, 2, 0b0111, 0);
}

#[test]
fn test_compare_lessequalgreater_positive1() {
    run_compare_test(1, 8, 0b1110, 1);
    run_compare_test(1, 8, 0b1111, 1);
}

#[test]
fn test_compare_lessequalgreater_positive2() {
    run_compare_test(8, 8, 0b1110, 1);
    run_compare_test(8, 8, 0b1111, 1);
}

#[test]
fn test_compare_lessequalgreater_positive3() {
    run_compare_test(9, 8, 0b1110, 1);
    run_compare_test(9, 8, 0b1111, 1);
}

#[test]
fn test_compare_less_unsigned_positive() {
    run_compare_test(0x1234, 0xABCD, 0b1000, 1);
}

#[test]
fn test_compare_less_unsigned_negative() {
    run_compare_test(0xABCD, 0x1234, 0b1000, 0);
}

#[test]
fn test_compare_greater_unsigned_positive() {
    run_compare_test(0xABCD, 0x1234, 0b0010, 1);
}

#[test]
fn test_compare_greater_unsigned_negative() {
    run_compare_test(0x1234, 0xABCD, 0b0010, 0);
}

#[test]
fn test_compare_less_signed_positive() {
    run_compare_test(0xABCD, 0x1234, 0b1001, 1);
}

#[test]
fn test_compare_less_signed_negative() {
    run_compare_test(0x1234, 0xABCD, 0b1001, 0);
}

#[test]
fn test_compare_greater_signed_positive() {
    run_compare_test(0x1234, 0xABCD, 0b0011, 1);
}

#[test]
fn test_compare_greater_signed_negative() {
    run_compare_test(0xABCD, 0x1234, 0b0011, 0);
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x5xxx-unary-functions
// The instruction is `0b0101 1010 0101 0110`, and register 5 contains the value 0x1234. Then this instruction will write the value 0xEDCB into register 6, because not(0x1234) = 0xEDCB.
#[test]
fn test_unary_doc1() {
    run_test(
        &[
            0x3534, 0x4512, // lw r5, 0x1234
            0x5A56, // not r6, r5
        ],
        &[],
        3,
        &[
            Expectation::ProgramCounter(3),
            Expectation::ActualNumSteps(3),
            Expectation::Register(5, 0x1234),
            Expectation::Register(6, 0xEDCB),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x5xxx-unary-functions
// The instruction is `0b0101 1001 0011 0011`, and register 3 contains the value 41. Then this instruction will write the value 42 into register 3, because incr(41) = 42.
#[test]
fn test_unary_doc2() {
    run_test(
        &[
            0x3329, // lw r3, 41
            0x5933, // incr r3
        ],
        &[],
        2,
        &[
            Expectation::ProgramCounter(2),
            Expectation::ActualNumSteps(2),
            Expectation::Register(3, 42),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

fn run_unary_test(function: u16, a: u16, result: u16) {
    run_test(
        &[
            0x3100 | (a & 0xFF),        // ↓
            0x4100 | ((a >> 8) & 0xFF), // lw r1, a
            0x5012 | (function << 8),   // unary.function r2, r1
        ],
        &[],
        3,
        &[
            Expectation::ProgramCounter(3),
            Expectation::ActualNumSteps(3),
            Expectation::Register(1, a),
            Expectation::Register(2, result),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_unary_decr() {
    // * If FFFF=1000, the computed function is "decr" (add 1), e.g. decr(41) = 40
    run_unary_test(0b1000, 41, 40);
    run_unary_test(0b1000, 0x0000, 0xFFFF);
    run_unary_test(0b1000, 0xABCD, 0xABCC);
}

#[test]
fn test_unary_incr() {
    // * If FFFF=1001, the computed function is "incr" (subtract 1), e.g. incr(41) = 42
    run_unary_test(0b1001, 41, 42);
    run_unary_test(0b1001, 0xFFFF, 0x0000);
    run_unary_test(0b1001, 0xABCD, 0xABCE);
}

#[test]
fn test_unary_not() {
    // * If FFFF=1010, the computed function is "not" (bite-wise logical negation), e.g. not(0x1234) = 0xEDCB
    run_unary_test(0b1010, 0x1234, 0xEDCB);
    run_unary_test(0b1010, 0x0F5A, 0xF0A5);
}

#[test]
fn test_unary_popcnt() {
    // * If FFFF=1011, the computed function is "popcnt" (population count), e.g. popcnt(0xFFFF) = 16, popcnt(0x0000) = 0
    //     * Note that there are no silly exceptions as there would be in x86.
    run_unary_test(0b1011, 0xFFFF, 16);
    run_unary_test(0b1011, 0x0000, 0);
    run_unary_test(0b1011, 0x1234, 5);
}

#[test]
fn test_unary_clz() {
    // * If FFFF=1100, the computed function is "clz" (count leading zeros), e.g. clz(0x8000) = 0, clz(0x0002) = 14
    run_unary_test(0b1100, 0x8000, 0);
    run_unary_test(0b1100, 0x0002, 14);
    run_unary_test(0b1100, 0xFFFF, 0);
    run_unary_test(0b1100, 0x0000, 16);
}

#[test]
fn test_unary_ctz() {
    // * If FFFF=1101, the computed function is "ctz" (count trailing zeros), e.g. ctz(0x8000) = 15, ctz(0x0002) = 1
    run_unary_test(0b1101, 0x8000, 15);
    run_unary_test(0b1101, 0x0002, 1);
    run_unary_test(0b1101, 0xFFFF, 0);
    run_unary_test(0b1101, 0x0000, 16);
}

#[test]
fn test_unary_rnd() {
    // * If FFFF=1110, the computed function is "rnd" (random number up to AND INCLUDING), e.g. rnd(5) = 3, rnd(5) = 5, rnd(5) = 0
    //     * Note that rnd must never result in a value larger than the argument, so rnd(5) must never generate 6 or even 0xFFFF.

    // The only argument with a predictable outcome:
    run_unary_test(0b1110, 0, 0);

    // The other cases aren't easily testable
}

#[test]
fn test_unary_rnd_inclusive() {
    run_test(
        &[
            0x3105, // lw r1, 5
            0x5E12, // rnd r2, r1
            0x8C21, // le r2 r1
            0x8620, // ge r2 r0
        ],
        &[],
        4,
        &[
            Expectation::ProgramCounter(4),
            Expectation::ActualNumSteps(4),
            // Can't easily check register 2 here.
            // So instead we use the VM to check that it is within bounds:
            Expectation::Register(0, 1),
            Expectation::Register(1, 1),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_unary_rnd_extreme() {
    // This test is flaky, and fails with a probability of roughly 0.00305%.
    // So if you see it fail twice in a row, something is broken for sure.
    run_test(
        &[
            0x31FF, // lw r1, 0xFFFF
            0x5E12, // rnd r2, r1
            0x8421, // eq r2 r1
            0x8420, // eq r2 r0
        ],
        &[],
        4,
        &[
            Expectation::ProgramCounter(4),
            Expectation::ActualNumSteps(4),
            // Can't easily check register 2 here.
            // So instead we use the VM to check that it is neither minimum nor maximum:
            Expectation::Register(0, 0),
            Expectation::Register(1, 0),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_unary_mov() {
    // * If FFFF=1111, the computed function is "mov" (move, identity function), e.g. mov(0x5678) = 0x5678
    run_unary_test(0b1111, 0x5678, 0x5678);
    run_unary_test(0b1111, 0x0002, 0x0002);
    run_unary_test(0b1111, 0xFFFF, 0xFFFF);
    run_unary_test(0b1111, 0x0000, 0x0000);
}

// https://github.com/BenWiederhake/tinyvm/blob/master/instruction-set-architecture.md#0x6xxx-basic-binary-functions
// The instruction is `0b0110 0010 0101 0110`, register 5 contains the value 0x0005, and register 6 contains the value 0x0007. Then this instruction will write the value 0x0023 into register 6, because 5 \* 7 = 35 = 0x0023.
#[test]
fn test_binary_doc() {
    run_test(
        &[
            0x3505, // lw r5, 5
            0x3607, // lw r6, 7
            0x6256, // mul r5 r6
        ],
        &[],
        3,
        &[
            Expectation::ProgramCounter(3),
            Expectation::ActualNumSteps(3),
            Expectation::Register(5, 5),
            Expectation::Register(6, 35),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

fn run_binary_test(a: u16, b: u16, function: u16, result: u16) {
    run_test(
        &[
            0x3100 | (a & 0xFF),        // ↓
            0x4100 | ((a >> 8) & 0xFF), // lw r1, a
            0x3200 | (b & 0xFF),        // ↓
            0x4200 | ((b >> 8) & 0xFF), // lw r2, b
            0x6012 | (function << 8),   // binary.function r2, r1
        ],
        &[],
        5,
        &[
            Expectation::ProgramCounter(5),
            Expectation::ActualNumSteps(5),
            Expectation::Register(1, a),
            Expectation::Register(2, result),
            Expectation::LastStep(StepResult::Continue),
        ],
    );
}

#[test]
fn test_binary_add() {
    // * If FFFF=0000, the computed function is "+" (overflowing addition), e.g. fn(0x1234, 0xABCD) = 0xBE01
    //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
    run_binary_test(0x1234, 0xABCD, 0b0000, 0xBE01);
    run_binary_test(0x0005, 0x0007, 0b0000, 0x000C);
    run_binary_test(0xFFFF, 0x0002, 0b0000, 0x0001);
}

#[test]
fn test_binary_sub() {
    // * If FFFF=0001, the computed function is "-" (overflowing subtraction), e.g. fn(0xBE01, 0xABCD) = 0x1234, fn(0x0007, 0x0009) = 0xFFFE
    //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
    run_binary_test(0xBE01, 0xABCD, 0b0001, 0x1234);
    run_binary_test(0x0007, 0x0009, 0b0001, 0xFFFE);
    run_binary_test(0x0009, 0x0007, 0b0001, 0x0002);
}

#[test]
fn test_binary_mul() {
    // * If FFFF=0010, the computed function is "*" (truncated multiplication, low word), e.g. fn(0x0005, 0x0007) = 0x0023, fn(0x1234, 0xABCD) = 0x4FA4
    //     * Note that there is no need to distinguish signedness, as the results would always bit-identical.
    run_binary_test(0x0005, 0x0007, 0b0010, 0x0023);
    run_binary_test(0x1234, 0xABCD, 0b0010, 0x4FA4);
    run_binary_test(0x0000, 0x1234, 0b0010, 0x0000);
    run_binary_test(0xFFFF, 0xFFFF, 0b0010, 0x0001);
}

#[test]
fn test_binary_mulh() {
    // * If FFFF=0011, the computed function is "*h" (truncated multiplication, high word), e.g. fn(0x0005, 0x0007) = 0x0000, fn(0x1234, 0xABCD) = 0x0C37
    //     * Note that there is no signed equivalent.
    run_binary_test(0x0005, 0x0007, 0b0011, 0x0000);
    run_binary_test(0x1234, 0xABCD, 0b0011, 0x0C37);
    run_binary_test(0xFFFF, 0xFFFF, 0b0011, 0xFFFE);
}

#[test]
fn test_binary_div_u() {
    // * If FFFF=0100, the computed function is "div.u" (unsigned division, rounded towards 0), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0x0009
    //     * The result of dividing by zero is 0xFFFF, the highest unsigned value.
    run_binary_test(0x0023, 0x0007, 0b0100, 0x0005);
    run_binary_test(0xABCD, 0x1234, 0b0100, 0x0009);
    run_binary_test(0x0001, 0x0000, 0b0100, 0xFFFF);

    run_binary_test(0x0022, 0x0007, 0b0100, 0x0004);
    run_binary_test(0x001D, 0x0007, 0b0100, 0x0004);
    run_binary_test(0x001C, 0x0007, 0b0100, 0x0004);
    run_binary_test(0x001B, 0x0007, 0b0100, 0x0003);
    run_binary_test(0x1234, 0xABCD, 0b0100, 0x0000);
    run_binary_test(0x0000, 0x0000, 0b0100, 0xFFFF);
    run_binary_test(0xFFFF, 0x0000, 0b0100, 0xFFFF);
    run_binary_test(0x0000, 0xFFFF, 0b0100, 0x0000);
    run_binary_test(0xFFFF, 0x7FFF, 0b0100, 0x0002);
    run_binary_test(0xFFFF, 0xFFFF, 0b0100, 0x0001);
    run_binary_test(0xFFFF, 0x0001, 0b0100, 0xFFFF);
}

#[test]
fn test_binary_div_s() {
    // * If FFFF=0101, the computed function is "div.s" (signed division, rounded towards 0), e.g. fn(0x0023, 0x0007) = 0x0005, fn(0xABCD, 0x1234) = 0xFFFC
    //     * The result of dividing by zero is 0x7FFF, the highest signed value.
    //     * We define fn(0x8000, 0xFFFF) = 0x8000.
    run_binary_test(0x0023, 0x0007, 0b0101, 0x0005);
    run_binary_test(0xABCD, 0x1234, 0b0101, 0xFFFC);
    run_binary_test(0x0001, 0x0000, 0b0101, 0x7FFF);
    run_binary_test(0x8000, 0xFFFF, 0b0101, 0x8000);

    // pos/pos, round towards 0:
    run_binary_test(0x0022, 0x0007, 0b0101, 0x0004);
    run_binary_test(0x001D, 0x0007, 0b0101, 0x0004);
    run_binary_test(0x001C, 0x0007, 0b0101, 0x0004);
    run_binary_test(0x001B, 0x0007, 0b0101, 0x0003);
    // neg/pos, round towards 0:
    run_binary_test(0xFFEA, 0x0007, 0b0101, 0xFFFD);
    run_binary_test(0xFFEB, 0x0007, 0b0101, 0xFFFD);
    run_binary_test(0xFFEC, 0x0007, 0b0101, 0xFFFE);
    run_binary_test(0xFFF1, 0x0007, 0b0101, 0xFFFE);
    run_binary_test(0xFFF2, 0x0007, 0b0101, 0xFFFE);
    run_binary_test(0xFFF3, 0x0007, 0b0101, 0xFFFF);
    run_binary_test(0xFFFF, 0x0001, 0b0101, 0xFFFF);
    // div by zero:
    run_binary_test(0x0000, 0x0000, 0b0101, 0x7FFF);
    run_binary_test(0xFFFF, 0x0000, 0b0101, 0x7FFF);
    // pos/neg, round towards -infinity:
    run_binary_test(0x1234, 0xABCD, 0b0101, 0x0000);
    run_binary_test(0x0000, 0xFFFF, 0b0101, 0x0000);
    run_binary_test(0x0015, 0xFFF9, 0b0101, 0xFFFD);
    run_binary_test(0x0014, 0xFFF9, 0b0101, 0xFFFE);
    run_binary_test(0x000F, 0xFFF9, 0b0101, 0xFFFE);
    run_binary_test(0x000E, 0xFFF9, 0b0101, 0xFFFE);
    run_binary_test(0x000D, 0xFFF9, 0b0101, 0xFFFF);
    // other:
    run_binary_test(0xFFFF, 0x7FFF, 0b0101, 0x0000);
    run_binary_test(0xFFFF, 0xFFFF, 0b0101, 0x0001);
}

#[test]
fn test_binary_mod_u() {
    // * If FFFF=0110, the computed function is "mod.u" (unsigned modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x07F9
    //     * The result of modulo by zero is 0x0000.
    //     * Note that if x = div.u(a, b) and y = mod.u(a, b), then add(mul(x, b), y) will usually result in a.
    run_binary_test(0x0023, 0x0007, 0b0110, 0x0000);
    run_binary_test(0xABCD, 0x1234, 0b0110, 0x07F9);
    run_binary_test(0x0001, 0x0000, 0b0110, 0x0000);

    run_binary_test(0x0022, 0x0007, 0b0110, 0x0006);
    run_binary_test(0x001D, 0x0007, 0b0110, 0x0001);
    run_binary_test(0x001C, 0x0007, 0b0110, 0x0000);
    run_binary_test(0x001B, 0x0007, 0b0110, 0x0006);
    run_binary_test(0x1234, 0xABCD, 0b0110, 0x1234);
    run_binary_test(0x0000, 0x0000, 0b0110, 0x0000);
    run_binary_test(0x0000, 0x0001, 0b0110, 0x0000);
    run_binary_test(0x0001, 0x0001, 0b0110, 0x0000);
    run_binary_test(0x0002, 0x0001, 0b0110, 0x0000);
    run_binary_test(0xFFFF, 0x0000, 0b0110, 0x0000);
    run_binary_test(0x0000, 0xFFFF, 0b0110, 0x0000);
    run_binary_test(0xFFFF, 0x7FFF, 0b0110, 0x0001);
    run_binary_test(0xFFFF, 0xFFFF, 0b0110, 0x0000);
    run_binary_test(0xFFFF, 0x0001, 0b0110, 0x0000);
}

#[test]
fn test_binary_mod_s() {
    // * If FFFF=0111, the computed function is "mod.s" (signed modulo), e.g. fn(0x0023, 0x0007) = 0x0000, fn(0xABCD, 0x1234) = 0x06D1
    //     * The result of modulo by zero is 0x0000.
    //     * Note that if x = div.s(a, b) and y = mod.s(a, b), then add(mul(x, b), y) will usually result in a.
    run_binary_test(0x0023, 0x0007, 0b0111, 0x0000);
    //run_binary_test(0xABCD, 0x1234, 0b0111, 0x06D1);
    run_binary_test(0x0001, 0x0000, 0b0111, 0x0000);

    // pos/pos:
    run_binary_test(0x0022, 0x0007, 0b0111, 0x0006);
    run_binary_test(0x001D, 0x0007, 0b0111, 0x0001);
    run_binary_test(0x001C, 0x0007, 0b0111, 0x0000);
    run_binary_test(0x001B, 0x0007, 0b0111, 0x0006);
    // neg/pos:
    run_binary_test(0xFFEA, 0x0007, 0b0111, 0xFFFF); // a = 0xFFEA = -22, x = 0xFFFD = -3, x*7=-21, need -1 to get to a
    run_binary_test(0xFFEB, 0x0007, 0b0111, 0x0000); // a = 0xFFEB = -21, x = 0xFFFD = -3, x*7=-21, need +0 to get to a
    run_binary_test(0xFFEC, 0x0007, 0b0111, 0xFFFA); // a = 0xFFEC = -20, x = 0xFFFE = -2, x*7=-14, need -6 to get to a
    run_binary_test(0xFFF1, 0x0007, 0b0111, 0xFFFF); // a = 0xFFF1 = -15, x = 0xFFFE = -2, x*7=-14, need -1 to get to a
    run_binary_test(0xFFF2, 0x0007, 0b0111, 0x0000); // a = 0xFFF2 = -14, x = 0xFFFE = -2, x*7=-14, need +0 to get to a
    run_binary_test(0xFFF3, 0x0007, 0b0111, 0xFFFA); // a = 0xFFF3 = -13, x = 0xFFFF = -1, x*7= -7, need -6 to get to a

    // mod by zero:
    run_binary_test(0x0000, 0x0000, 0b0111, 0x0000);
    run_binary_test(0xFFFF, 0x0000, 0b0111, 0x0000);
    // mod by one:
    run_binary_test(0x0000, 0x0001, 0b0111, 0x0000);
    run_binary_test(0xFFFF, 0x0001, 0b0111, 0x0000);
    // mod by minus one:
    run_binary_test(0x0000, 0xFFFF, 0b0111, 0x0000);
    run_binary_test(0x0001, 0xFFFF, 0b0111, 0x0000);
    run_binary_test(0xFFFF, 0xFFFF, 0b0111, 0x0000);
    run_binary_test(0x8000, 0xFFFF, 0b0111, 0x0000);
    // pos/neg:
    run_binary_test(0x1234, 0xABCD, 0b0111, 0x1234);
    run_binary_test(0x0015, 0xFFF9, 0b0111, 0x0000);
    run_binary_test(0x0014, 0xFFF9, 0b0111, 0x0006);
    run_binary_test(0x000F, 0xFFF9, 0b0111, 0x0001);
    run_binary_test(0x000E, 0xFFF9, 0b0111, 0x0000);
    // other:
    run_binary_test(0xFFFF, 0x7FFF, 0b0111, 0xFFFF);
}

#[test]
fn test_binary_and() {
    // * If FFFF=1000, the computed function is "and" (bitwise and), e.g. fn(0x5500, 0x5050) = 0x5000
    run_binary_test(0x5500, 0x5050, 0b1000, 0x5000);
    run_binary_test(0x000C, 0x000A, 0b1000, 0x0008);
    run_binary_test(0x0000, 0xFFFF, 0b1000, 0x0000);
    run_binary_test(0xFFFF, 0xFFFF, 0b1000, 0xFFFF);
}

#[test]
fn test_binary_or() {
    // * If FFFF=1001, the computed function is "or" (bitwise inclusive or), e.g. fn(0x5500, 0x5050) = 0x5550
    run_binary_test(0x5500, 0x5050, 0b1001, 0x5550);
    run_binary_test(0x000C, 0x000A, 0b1001, 0x000E);
    run_binary_test(0x0000, 0xFFFF, 0b1001, 0xFFFF);
    run_binary_test(0xFFFF, 0xFFFF, 0b1001, 0xFFFF);
    run_binary_test(0x0000, 0x0000, 0b1001, 0x0000);
}

#[test]
fn test_binary_xor() {
    // * If FFFF=1010, the computed function is "xor" (bitwise exclusive or), e.g. fn(0x5500, 0x5050) = 0x0550
    run_binary_test(0x5500, 0x5050, 0b1010, 0x0550);
    run_binary_test(0x000C, 0x000A, 0b1010, 0x0006);
    run_binary_test(0x0000, 0xFFFF, 0b1010, 0xFFFF);
    run_binary_test(0xFFFF, 0xFFFF, 0b1010, 0x0000);
    run_binary_test(0x0000, 0x0000, 0b1010, 0x0000);
}

#[test]
fn test_binary_sl() {
    // * If FFFF=1011, the computed function is "sl" (bitshift left, filling the least-significant bits with zero), e.g. fn(0x1234, 0x0001) = 0x2468, fn(0xFFFF, 0x0010) = 0x0000
    //     * Note that there are no silly exceptions as there would be in x86.
    run_binary_test(0x1234, 0x0001, 0b1011, 0x2468);
    run_binary_test(0xFFFF, 0x0010, 0b1011, 0x0000);

    run_binary_test(0x1234, 0x0000, 0b1011, 0x1234);
    run_binary_test(0x1234, 0x0010, 0b1011, 0x0000);
    run_binary_test(0x1234, 0x0008, 0b1011, 0x3400);
    run_binary_test(0xFFFF, 0x000B, 0b1011, 0xF800);
    run_binary_test(0xFFFF, 0x000C, 0b1011, 0xF000);
    run_binary_test(0xFFFF, 0x000D, 0b1011, 0xE000);
    run_binary_test(0xFFFF, 0x000E, 0b1011, 0xC000);
    run_binary_test(0xFFFF, 0x000F, 0b1011, 0x8000);
    run_binary_test(0xFFFF, 0x0011, 0b1011, 0x0000);
    run_binary_test(0xFFFF, 0x0012, 0b1011, 0x0000);
}

#[test]
fn test_binary_srl() {
    // * If FFFF=1100, the computed function is "srl" (logical bitshift right, filling the most significant bits with zero), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0x0000
    run_binary_test(0x2468, 0x0001, 0b1100, 0x1234);
    run_binary_test(0xFFFF, 0x0010, 0b1100, 0x0000);

    run_binary_test(0x1234, 0x0000, 0b1100, 0x1234);
    run_binary_test(0x1234, 0x0010, 0b1100, 0x0000);
    run_binary_test(0x1234, 0x0008, 0b1100, 0x0012);
    run_binary_test(0xFFFF, 0x000B, 0b1100, 0x001F);
    run_binary_test(0xFFFF, 0x000C, 0b1100, 0x000F);
    run_binary_test(0xFFFF, 0x000D, 0b1100, 0x0007);
    run_binary_test(0xFFFF, 0x000E, 0b1100, 0x0003);
    run_binary_test(0xFFFF, 0x000F, 0b1100, 0x0001);
    run_binary_test(0xFFFF, 0x0011, 0b1100, 0x0000);
    run_binary_test(0xFFFF, 0x0012, 0b1100, 0x0000);
}

#[test]
fn test_binary_sra() {
    // * If FFFF=1101, the computed function is "sra" (arithmetic bitshift right, filling the most significant bits with the sign-bit), e.g. fn(0x2468, 0x0001) = 0x1234, fn(0xFFFF, 0x0010) = 0xFFFF
    //     * Note that the right-hand side is interpreted as unsigned, so fn(0x1234, 0xFFFF) = 0x0000, because here 0xFFFF = 65536 (and not -1)
    run_binary_test(0x2468, 0x0001, 0b1101, 0x1234);
    run_binary_test(0xFFFF, 0x0010, 0b1101, 0xFFFF);
    run_binary_test(0x1234, 0xFFFF, 0b1101, 0x0000);

    run_binary_test(0x1234, 0x0000, 0b1101, 0x1234);
    run_binary_test(0x1234, 0x0010, 0b1101, 0x0000);
    run_binary_test(0x1234, 0x0011, 0b1101, 0x0000);
    run_binary_test(0x1234, 0x0008, 0b1101, 0x0012);
    run_binary_test(0xFFFF, 0x000B, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x000C, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x000D, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x000E, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x000F, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x0011, 0b1101, 0xFFFF);
    run_binary_test(0xFFFF, 0x0012, 0b1101, 0xFFFF);

    run_binary_test(0x8000, 0x0000, 0b1101, 0x8000);
    run_binary_test(0x8000, 0x0001, 0b1101, 0xC000);
    run_binary_test(0x8000, 0x000B, 0b1101, 0xFFF0);
    run_binary_test(0x8000, 0x000C, 0b1101, 0xFFF8);
    run_binary_test(0x8000, 0x000D, 0b1101, 0xFFFC);
    run_binary_test(0x8000, 0x000E, 0b1101, 0xFFFE);
    run_binary_test(0x8000, 0x000F, 0b1101, 0xFFFF);
    run_binary_test(0x8000, 0x0011, 0b1101, 0xFFFF);
    run_binary_test(0x8000, 0x0012, 0b1101, 0xFFFF);
}

// FIXME: Implement and test "exp" instruction
// FIXME: Implement and test "root" instruction

#[test]
fn test_fibonacci() {
    #[rustfmt::skip] // Would break the labels. See https://github.com/rust-lang/rustfmt/issues/5630
    run_test(
        &[
            0x3018, // lw r0, 24
            0x3101, // lw r1, 1
                    // .label start:
            0x6012, // add r1 r2
            0x5800, // decr r0
            0x2002, // sw r0, r2
            0x6021, // add r2 r1
            0x5800, // decr r0
            0x2001, // sw r0, r1
            0x9085, // b r0 start // (offset is -0x6)
            0x102A, // ret
        ],
        &[],
        0xFFFF,
        &[
            Expectation::ActualNumSteps(2 + (24 / 2) * 7),
            Expectation::ProgramCounter(9),
            Expectation::Data(23, 1),
            Expectation::Data(22, 2),
            Expectation::Data(21, 3),
            Expectation::Data(20, 5),
            Expectation::Data(19, 8),
            Expectation::Data(18, 13),
            Expectation::Data(17, 21),
            Expectation::Data(16, 34),
            Expectation::Data(15, 55),
            Expectation::Data(14, 89),
            Expectation::Data(13, 144),
            Expectation::Data(12, 233),
            Expectation::Data(11, 377),
            Expectation::Data(10, 610),
            Expectation::Data(9, 987),
            Expectation::Data(8, 1597),
            Expectation::Data(7, 2584),
            Expectation::Data(6, 4181),
            Expectation::Data(5, 6765),
            Expectation::Data(4, 10946),
            Expectation::Data(3, 17711),
            Expectation::Data(2, 28657),
            Expectation::Data(1, 46368),
            Expectation::Data(0, 9489), // 75025 & 0xFFFF
            Expectation::Register(0, 0),
            Expectation::Register(1, 9489),
            Expectation::Register(2, 46368),
            Expectation::LastStep(StepResult::Return(0)),
        ],
    );
}
