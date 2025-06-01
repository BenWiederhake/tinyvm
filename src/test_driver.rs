use crate::vm::{Segment, StepResult, VirtualMachine};

use std::fmt::{Display, Formatter, Result};

use enumn::N;

pub const TEST_DRIVER_ID: u16 = 0x0003;
pub const TEST_DRIVER_LAYOUT_VERSION: u16 = 0x0001;

#[repr(u16)]
#[derive(Debug, Eq, Clone, Copy, PartialEq)]
enum TesteeExecutionResult {
    // https://github.com/BenWiederhake/tinyvm/blob/master/data-layout/0003_test_driver.md#executing-the-testee
    // The testee will continue to execute, until it either:
    // - yields, in which case 0x0000 and the yield value are written to register 0 and 1 of the driver, respectively;
    Yielded = 0x0000,
    // - or the allotted time is up, in which case 0x0001 is written to register 0 of the driver;
    Timeout = 0x0001,
    // - or the testee attempts to execute an illegal instruction, in which case 0xFFFF (i.e. -1) is written to register 0 of the driver.
    IllegalInstruction = 0xFFFF,
}

#[repr(u16)]
#[derive(Debug, Eq, Clone, Copy, N, PartialEq)]
enum DriverCommand {
    // https://github.com/BenWiederhake/tinyvm/blob/master/data-layout/0003_test_driver.md#miscellaneous
    // - When the driver yields with value 1, the testee will now be executed until it stops by itself. See [Executing the testee](#executing-the-testee) section.
    ExecuteTestee = 0x0001,
    // - When the driver yields with value 2, it indicates that it is done, and returns the test results. See [Returning test results](#returning-test-results) section.
    Done = 0x0002,
    // - When the driver yields with value 3, some of the registers of the testee will be overwritten/read. See [Reading/overwriting the testee registers](#readingoverwriting-the-testee-registers).
    AccessRegisters = 0x0003,
    // - When the driver yields with value 4, some of the testee data segment will be overwritten. See [Overwriting the testee data segment](#overwriting-the-testee-data-segment).
    OverwriteData = 0x0004,
    // - When the driver yields with value 5, some of the testee data segment will be read. See [Reading the testee data segment](#reading-the-testee-data-segment).
    ReadData = 0x0005,
    // - When the driver yields with value 6, some of the testee instruction segment will be read. See [Reading the testee instruction segment](#reading-the-testee-instruction-segment).
    ReadInstructions = 0x0006,
    // - When the driver yields with value 7, the testee's data segment, registers and program counter will be reset to all-zeros.
    ResetTesteeVM = 0x0007,
    // - When the driver yields with value 8, the testee's allotted time is reset. See [Resetting the time limit](#resetting-the-time-limit).
    ResetTimeLimit = 0x0008,
    // - When the driver yields with value 9, the testee's program counter is set to the value of register 1 of the driver.
    SetProgramCounter = 0x0009,
    // - Any other value in register 0 is interpreted as a fatal error of the test suite, and results in a corresponding output.
    Illegal = 0xFFFF,
}

impl From<u16> for DriverCommand {
    fn from(value: u16) -> Self {
        Self::n(value).unwrap_or(DriverCommand::Illegal)
    }
}

#[derive(Debug)]
pub struct TestDriverData {
    vm_driver: VirtualMachine,
    vm_testee: VirtualMachine,
    driver_insns: u64,
    testee_insns: u64,
    testee_limit: u64,
    // If "testee_remaining" is > 0, then the focus is on the testee.
    // Note that if the testee does something illegal (e.g. illegal instruction), this is set to 0.
    testee_remaining: u64,
}

impl TestDriverData {
    pub fn new(driver_instructions: Segment, testee_instructions: Segment) -> Self {
        let mut driver_data = Segment::new_zeroed();
        let testee_data = Segment::new_zeroed();
        // https://github.com/BenWiederhake/tinyvm/blob/master/data-layout/0003_test_driver.md
        // * The data segment at address 0xFFFF of the driver is initialized to 0x0003 (meaning "test\_driver")
        // * The data segment at address 0xFFFE of the driver is initialized to 0x0001 (meaning "version 1")
        driver_data[0xFFFF] = TEST_DRIVER_ID;
        driver_data[0xFFFE] = TEST_DRIVER_LAYOUT_VERSION;
        let vm_driver = VirtualMachine::new(driver_instructions, driver_data);
        let vm_testee = VirtualMachine::new(testee_instructions, testee_data);
        Self {
            vm_driver,
            vm_testee,
            driver_insns: 0,
            testee_insns: 0,
            testee_limit: 0x0000_FFFF_FFFF_FFFF,
            testee_remaining: 0,
        }
    }

    pub fn do_step(&mut self) -> Option<TestResult> {
        if self.testee_remaining > 0 {
            self.testee_remaining -= 1;
            self.testee_insns += 1;
            match self.vm_testee.step() {
                StepResult::Continue | StepResult::DebugDump => None,
                StepResult::IllegalInstruction(insn) => {
                    self.vm_driver
                        .set_register(0, TesteeExecutionResult::IllegalInstruction as u16);
                    self.vm_driver.set_register(1, insn);
                    None
                }
                StepResult::Yield(yield_value) => {
                    self.vm_driver
                        .set_register(0, TesteeExecutionResult::Yielded as u16);
                    self.vm_driver.set_register(1, yield_value);
                    self.testee_remaining = 0;
                    None
                }
            }
        } else {
            self.driver_insns += 1;
            match self.vm_driver.step() {
                StepResult::Continue | StepResult::DebugDump => None,
                StepResult::IllegalInstruction(insn) => Some(TestResult::IllegalInstruction(insn)),
                StepResult::Yield(cmd) => self.handle_driver_yield(cmd),
            }
        }
    }

    fn handle_driver_yield(&mut self, command: u16) -> Option<TestResult> {
        match DriverCommand::from(command) {
            DriverCommand::ExecuteTestee => self.handle_execute_testee(),
            DriverCommand::Done => self.handle_done(),
            DriverCommand::AccessRegisters => self.handle_access_registers(),
            DriverCommand::OverwriteData => self.handle_overwrite_data(),
            DriverCommand::ReadData => self.handle_read_data(),
            DriverCommand::ReadInstructions => self.handle_read_instructions(),
            DriverCommand::ResetTesteeVM => self.handle_reset_testee_vm(),
            DriverCommand::ResetTimeLimit => self.handle_reset_time_limit(),
            DriverCommand::SetProgramCounter => self.handle_set_program_counter(),
            DriverCommand::Illegal => {
                return Some(TestResult::IllegalYield(command));
            }
        }
        None
    }

    fn handle_execute_testee(&mut self) {
        // Already set "testee timeout" as "response" in register 0, so that the timeout case doesn't have to be recognized separately.
        self.vm_driver
            .set_register(0, TesteeExecutionResult::Timeout as u16);
        unimplemented!()
    }

    fn handle_done(&mut self) {
        unimplemented!()
    }

    fn handle_access_registers(&mut self) {
        unimplemented!()
    }

    fn handle_overwrite_data(&mut self) {
        unimplemented!()
    }

    fn handle_read_data(&mut self) {
        unimplemented!()
    }

    fn handle_read_instructions(&mut self) {
        unimplemented!()
    }

    fn handle_reset_testee_vm(&mut self) {
        unimplemented!()
    }

    fn handle_reset_time_limit(&mut self) {
        unimplemented!()
    }

    fn handle_set_program_counter(&mut self) {
        unimplemented!()
    }

    pub fn conclude(&mut self, total_budget: u64) -> TestResult {
        while self.driver_insns + self.testee_insns < total_budget {
            if let Some(result) = self.do_step() {
                return result;
            }
        }
        TestResult::Timeout
    }
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub struct IndividualResult {
    result_value: u16,
    // TODO: Enable test drivers to also emit test names or error messages?
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub enum TestResult {
    IllegalInstruction(u16),
    IllegalYield(u16),
    Timeout,
    Completed(Vec<IndividualResult>),
}

impl Display for TestResult {
    fn fmt(&self, f: &mut Formatter) -> Result {
        todo!()
    }
}

pub fn run_and_print_tests(
    driver_instructions: &Segment,
    testee_instructions: &Segment,
    total_budget: u64,
) {
    let mut test_driver_data =
        TestDriverData::new(driver_instructions.clone(), testee_instructions.clone());
    let result = test_driver_data.conclude(total_budget);
    // TODO: Verbose mode? Quiet mode?
    println!("{}", result);
    eprintln!("{:?}", result);
}

#[cfg(test)]
mod test_test_driver {
    use super::*;

    #[test]
    fn test_command_parsing() {
        assert_eq!(
            DriverCommand::ExecuteTestee,
            DriverCommand::from(DriverCommand::ExecuteTestee as u16)
        );
        assert_eq!(
            DriverCommand::Done,
            DriverCommand::from(DriverCommand::Done as u16)
        );
        assert_eq!(
            DriverCommand::AccessRegisters,
            DriverCommand::from(DriverCommand::AccessRegisters as u16)
        );
        assert_eq!(
            DriverCommand::Illegal,
            DriverCommand::from(DriverCommand::Illegal as u16)
        );
        assert_eq!(DriverCommand::Illegal, DriverCommand::from(0x1234));
        assert_eq!(DriverCommand::Illegal, DriverCommand::from(0xABCD));
        assert_eq!(DriverCommand::Illegal, DriverCommand::from(0xFFFF));
        assert_eq!(DriverCommand::Illegal, DriverCommand::from(0x0000));
    }

    fn run_test(
        driver_instructions_prefix: &[u16],
        testee_instructions_prefix: &[u16],
        total_budget: u64,
    ) -> (TestDriverData, TestResult) {
        let driver_insns = Segment::from_prefix(driver_instructions_prefix);
        let testee_insns = Segment::from_prefix(testee_instructions_prefix);
        let mut test_driver_data = TestDriverData::new(driver_insns, testee_insns);
        let result = test_driver_data.conclude(total_budget);
        (test_driver_data, result)
    }

    #[test]
    fn test_no_budget() {
        let (test_driver_data, result) = run_test(&[], &[], 0);
        assert_eq!(result, TestResult::Timeout);
        assert_eq!(test_driver_data.driver_insns, 0);
    }

    #[test]
    fn test_illegal_instruction() {
        let (test_driver_data, result) = run_test(&[0x0000], &[], 999);
        // Driver tries to execute instruction 0x0000, which is an illegal instruction by design.
        assert_eq!(result, TestResult::IllegalInstruction(0x0000));
        assert_eq!(test_driver_data.driver_insns, 1);
    }

    #[test]
    fn test_illegal_instruction_late() {
        let (test_driver_data, result) = run_test(
            &[
                0x5F00, // nop
                0x102C, // debug
                0x5F00, // nop
                0xFFFF, // ill2
            ],
            &[],
            999,
        );
        // Driver tries to execute instruction 0xFFFF, which is an illegal instruction by design.
        assert_eq!(result, TestResult::IllegalInstruction(0xFFFF));
        assert_eq!(test_driver_data.driver_insns, 4);
    }

    #[test]
    fn test_illegal_yield() {
        let (test_driver_data, result) = run_test(
            &[
                0x3042, // lw r0, 0x42
                0x102A, // yield
            ],
            &[],
            999,
        );
        // Driver tries to yield with 0x42, which is not a legal command.
        assert_eq!(result, TestResult::IllegalYield(0x0042));
        assert_eq!(test_driver_data.driver_insns, 2);
    }

    #[test]
    fn test_illegal_yield_ffff() {
        let (test_driver_data, result) = run_test(
            &[
                0x30FF, // lw r0, 0xFFFF
                0x5F00, // nop
                0x102A, // yield
            ],
            &[],
            999,
        );
        // Driver tries to yield with 0xFFFF, which is not a legal command.
        assert_eq!(result, TestResult::IllegalYield(0xFFFF));
        assert_eq!(test_driver_data.driver_insns, 3);
    }

    // TODO: testee stop reason passing
    // TODO: All the other behaviors
}

#[cfg(test)]
mod test_result_printing {
    use super::*;

    #[test]
    fn test_anything() {
        todo!();
    }
}
