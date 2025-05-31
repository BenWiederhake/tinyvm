use crate::vm::{Segment, StepResult, VirtualMachine};

use std::fmt::{Display, Formatter, Result};

pub const TEST_DRIVER_ID: u16 = 0x0003;
pub const TEST_DRIVER_LAYOUT_VERSION: u16 = 0x0001;

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
            unimplemented!() // Testee step
        } else {
            unimplemented!() // Driver step
            // VM
            // If valid, add total insn
        }
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
    fn test_no_budget() {
        let driver_insns = Segment::new_zeroed();
        let testee_insns = Segment::new_zeroed();
        let mut test_driver_data = TestDriverData::new(driver_insns, testee_insns);
        let result = test_driver_data.conclude(0);
        // If any instruction got executed, it would be instruction 0x0000, which is an illegal instruction by design.
        assert_eq!(result, TestResult::Timeout);
    }
}

#[cfg(test)]
mod test_result_printing {
    use super::*;

    #[test]
    fn test_anything() {
        todo!();
    }
}
