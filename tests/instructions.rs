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
#[ignore = "jump-immediate not yet implemented"]
fn test_time_jump() {
    run_test(
        &[0xA003, 0, 0, 0, 0, 0x102D],
        &[],
        2,
        &[
            Expectation::ActualNumSteps(2),
            Expectation::ProgramCounter(6),
            Expectation::LastStep(StepResult::Continue),
            Expectation::Register(0, 0x0000),
            Expectation::Register(1, 0x0000),
            Expectation::Register(2, 0x0000),
            Expectation::Register(3, 0x0002),
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
#[ignore = "load immediate high not implemented"]
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
