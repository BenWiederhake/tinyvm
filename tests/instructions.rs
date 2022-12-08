use tinyvm::{Segment, StepResult, VirtualMachine};

enum Expectation {
    ActualNumSteps(u16),
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

    for expectation in expectations {
        match expectation {
            Expectation::ActualNumSteps(expected_steps) => {
                println!("Expecting {} actual steps", expected_steps);
                assert_eq!(*expected_steps, actual_steps);
            }
            Expectation::Data(address, expected_data) => {
                println!(
                    "Expecting word {:4X} at address {:4X}",
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
                    "Expecting register {} to contain {:4X}",
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
