# Test driver conventions

## Miscellaneous

Enables one VM (the "driver") to run some tests on an associated VM-under-test (the "testee"), and indicates which tests, if any, failed/skipped/succeeded.

In particular:
- At the beginning of execution, the data segment, registers and program counter of the driver and the testee are initialized to all-zeros, except for:
    * The data segment at address 0xFFFF of the driver is initialized to 0x0003 (meaning "test\_driver")
    * The data segment at address 0xFFFE of the driver is initialized to 0x0001 (meaning "version 1")
- When the driver yields with value 1, the testee will now be executed until it stops by itself. See [Executing the testee](#executing-the-testee) section.
- When the driver yields with value 2, it indicates that it is done, and returns the test results. See [Returning test results](#returning-test-results) section.
- When the driver yields with value 3, some of the registers of the testee will be overwritten/read. See [Reading/overwriting the testee registers](#readingoverwriting-the-testee-registers).
- When the driver yields with value 4, some of the testee data segment will be overwritten. See [Overwriting the testee data segment](#overwriting-the-testee-data-segment).
- When the driver yields with value 5, some of the testee data segment will be read. See [Reading the testee data segment](#reading-the-testee-data-segment).
- When the driver yields with value 6, some of the testee instruction segment will be read. See [Reading the testee instruction segment](#reading-the-testee-instruction-segment).
- When the driver yields with value 7, the testee's data segment, registers and program counter will be reset to all-zeros.
- When the driver yields with value 8, the testee's allotted time is reset. See [Resetting the time limit](#resetting-the-time-limit).
- When the driver yields with value 9, the testee's program counter is set to the value of register 1 of the driver.
- Any other value in register 0 is interpreted as a fatal error of the test suite, and results in a corresponding output.

Of particular note is that the time taken by the testee is subtracted from the total time budget of the test driver. Therefore, the driver should either attempt to restrict the testee's time, or live with the fact that a timeout results in very uninformative output.

## Executing the testee

With commands (yield values) 3 through 10, the test driver can control the exact setup of the testee, but only command (yield value) 1 transfers execution to the testee.

The testee will continue to execute, until it either:
- yields, in which case 0x0000 and the yield value are written to register 0 and 1 of the driver, respectively;
- or the allotted time is up, in which case 0x0001 is written to register 0 of the driver;
- or the testee attempts to execute an illegal instruction, in which case 0xFFFF (i.e. -1) is written to register 0 of the driver.

## Returning test results

In order to indicate test results, the driver must load the number of executed tests into register 1, as well as write the following into its data segment:
- For each test, the corresponding location (i.e. location 0x0000 for the first test, and location 0x000A for the eleventh test) must contain a result indicator:
    * 1 for "pass"
    * 2 for "fail"
    * 3 for "fatal error"
    * 4 for "skip"
    * all other values are considered an error of the test driver.
- After these values, the next two words must be 0x650D and 0x4585. (These are the first four bytes of SHA256(b"test driver result\n"), and serve as a kind of sanity check.)

This means that the maximum number of indicated tests is 65534, although it presumably becomes impractical already around a thousand tests.

TODO Example

## Reading/overwriting the testee registers

Register 1 is interpreted as a bitmap, indicating which registers shall be written. The
least-significant bit corresponds to register 0, the most significant bit corresponds to register 15.
The execution environment also reads the data segment at addresses 0x0000 through 0x000F, and
(for each bit that is set to 1) overwrites the testee's register with the word found in the
driver's data segment.

Register 2 is the offset used for the data segment access. The pointed-to region may cross the wrap-around point.

After this operation, the execution environment writes the (updated) values of all testee registers to the data segment of the driver, again in the slice "register 2 plus 0x0000" through "register 2 plus 0x000F".

Example:
- The testee already has value 0x1234 in register 7 from some prior instructions.
- The driver has written the value 0xABCD at location 0x0105 of its data segment.
- The driver loads the value 3 into register 0 and 16 (0b0000000000010000) into register 1.
- The driver loads the value 0x0100 into register 0 and 16 (0b0000000000010000) into register 1.
- The driver executes instruction 0x102A (`yield`).
- The execution environment recognizes this as a request to write the value 0xABCD into register 5 of the testee, and modifies none of the other registers.
- The execution environment writes the values of the testee's register to the data segment of the driver. At the addresses 0x0105 and 0x0107 in particular, it writes the values 0xABCD and 0x1234, respectively. (Note that the write-back of register 5 is effectively a no-op.)

## Overwriting the testee data segment

Register 1, 2, and 3 are used as the destination pointer (in the testee's data segment), source pointer (in the driver's data segment), and length (in number of words). This is analogous to the C standard library function memcpy.

Example:
- The testee's data segment contains the value 0x1234 at location 0x0007.
- The driver's data segment contains the value 0xABCD at location 0x000A.
- The driver's data segment contains the value 0x5678 at location 0x000B.
- The driver loads into registers 0 through 3 the values 4 ("overwrite data segment"), 0x0007, 0x000A, and 0x0002.
- The driver executes instruction 0x102A (`yield`).
- The execution environment recognizes this as a request to overwrite the testee's data segment, by writing the values 0xABCD and 0x5678 to the locations 0x0007 and 0x0008 respectively.

## Reading the testee data segment

TODO: Similar to the previous, but destination is the driver

## Reading the testee instruction segment

TODO: Similar to the previous, but destination is the driver

## Resetting the time limit

Register 1, 2, and 3 are interpreted as an unsigned 48-bit number N (with register 1 carrying the most significant bits, and register 3 carrying the least significant bits, similar to the 0x102D `time` instruction).

By default, that value is `2**48 - 1 = 0xFFFF_FFFF_FFFF = 281474976710655`.

Whenever execution is handed to the testee, the maximum number of instructions it may run is determined by N (the above number), and R, the remaining number of instructions in the test drivers overall budget.
- If N is zero, that's a fatal error.
- If N is non-zero, the limit is min(N, R)

TODO: Example
