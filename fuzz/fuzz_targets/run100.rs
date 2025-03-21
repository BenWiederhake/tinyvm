#![no_main]
extern crate tinyvm;

use libfuzzer_sys::fuzz_target;
use std::cmp::min;
use tinyvm::{Segment, StepResult, VirtualMachine};

fuzz_target!(|data: &[u8]| {
    let mut seg_insn = Segment::new_zeroed();
    for index in 0..min(65536, data.len() / 2) {
        let hi = data[index] as u16;
        let lo = data[index + 1] as u16;
        seg_insn[index as u16] = (hi << 8) | lo;
    }
    let seg_data = Segment::new_zeroed();
    let mut vm = VirtualMachine::new(seg_insn, seg_data);
    let mut last_step_result = StepResult::Continue;
    for _ in 0..100 {
        last_step_result = vm.step();
        if matches!(last_step_result, StepResult::IllegalInstruction(_)) {
            break;
        }
        // Continue even on DebugDump and Yield.
    }
    println!("last step: {last_step_result:?}");
    println!("regs: {:?}", vm.get_registers());
    println!("data:\n{:?}", vm.get_data());
});
