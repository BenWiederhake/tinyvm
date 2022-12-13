#!/usr/bin/env python3

import sys

SEGMENT_LENGTH = 131072
ASM_COMMANDS = dict()
DEBUG_OUTPUT = False
ERROR_OUTPUT = True


def asm_command(fn):
    name = fn.__name__
    prefix = "parse_command_"
    assert name.startswith(prefix), name
    command_name = name[len(prefix) :]
    global ASM_COMMANDS
    assert command_name not in ASM_COMMANDS
    ASM_COMMANDS[command_name] = fn
    return fn


class Assembler:
    def __init__(self):
        self.segment_words = [0] * (SEGMENT_LENGTH // 2)
        self.current_lineno = None
        self.current_pointer = 0x0000

    def error(self, msg):
        if DEBUG_OUTPUT or ERROR_OUTPUT:
            print(f"line {self.current_lineno}: {msg}", file=sys.stderr)
            # TODO: Do something more clever?
        return False

    def push_word(self, word):
        if DEBUG_OUTPUT:
            print(f"  pushing {word:04X}")
        assert 0 <= word <= 0xFFFF
        if self.segment_words[self.current_pointer] != 0:
            return self.error(
                f"Would overwrite word {self.segment_words[self.current_pointer]} at {self.current_pointer:04X}."
            )
        self.segment_words[self.current_pointer] = word
        self.current_pointer += 1
        self.current_pointer %= SEGMENT_LENGTH // 2
        return True

    def parse_reg(self, reg_string, context):
        # TODO: Add register alias support?
        if not reg_string.startswith("r"):
            self.error(
                f"Cannot parse register for {context}: Expected register (beginning with 'r'), "
                f"instead got '{reg_string}'. Try something like 'r0' instead."
            )
            return None
        number_part = reg_string[len("r") :]
        try:
            number = int(number_part)
        except ValueError:
            self.error(
                f"Cannot parse register for {context}: Expected register with numeric index, "
                f"instead got '{reg_string}'. Try something like 'r0' instead."
            )
            return None
        if "_" in number_part:
            self.error(
                f"Cannot parse register for {context}: Refusing underscores in register index "
                f"'{reg_string}'. Try something like 'r0' instead."
            )
            return None
        if number < 0 or number >= 16:
            self.error(
                f"Cannot parse register for {context}: Expected register with index in 0,1,…,15, "
                f"instead got '{reg_string}'. Try something like 'r0' instead."
            )
            return None
        return number

    @asm_command
    def parse_command_ret(self, command, args):
        if args != "":
            return self.error(
                f"Command 'ret' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102A)

    @asm_command
    def parse_command_ill(self, command, args):
        if args != "":
            return self.error(
                f"Command 'ill' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0xFFFF)

    @asm_command
    def parse_command_cpuid(self, command, args):
        if args != "":
            return self.error(
                f"Command 'cpuid' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102B)

    @asm_command
    def parse_command_debug(self, command, args):
        if args != "":
            return self.error(
                f"Command 'debug' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102C)

    @asm_command
    def parse_command_time(self, command, args):
        if args != "":
            return self.error(
                f"Command 'time' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102D)

    @asm_command
    def parse_command_sw(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command 'sw' expects exactly two arguments, got '{arg_list}' instead."
            )
        # TODO: Support immediates?
        addr_register = self.parse_reg(arg_list[0], "first argument to sw")
        if addr_register is None:
            # Error already reported
            return False
        value_register = self.parse_reg(arg_list[1], "second argument to sw")
        if value_register is None:
            # Error already reported
            return False
        assert 0 <= addr_register < 16
        assert 0 <= value_register < 16
        return self.push_word(0x2000 | (addr_register << 4) | value_register)

    def parse_line(self, line, lineno):
        self.current_lineno = lineno
        line = line.split("#")[0]
        line = line.strip()
        if not line:
            # Nothing to do here
            return True
        if " " in line:
            command, args = line.split(" ", 1)
        else:
            command = line
            args = ""
        if DEBUG_OUTPUT:
            print(f"{lineno}: {line}  # {command=} {args=}")
        command_fn = ASM_COMMANDS.get(command)
        if command_fn is None:
            return self.error(
                f"Command '{command}' not found. Did you mean any of {ASM_COMMANDS.keys()}' instead?"
            )

        return command_fn(self, command, args)

    def segment_bytes(self):
        segment = bytearray(SEGMENT_LENGTH)
        for i, word in enumerate(self.segment_words):
            segment[2 * i] = word >> 8
            segment[2 * i + 1] = word & 0xFF
        return bytes(segment)


def compile_to_segment(asm_text):
    asm = Assembler()
    for i, line in enumerate(asm_text.split("\n")):
        if not asm.parse_line(line, i):
            return None
    return asm.segment_bytes()


def run_on_files(infile, outfile):
    with open(infile, "r") as fp:
        asm_text = fp.read()
    segment = compile_to_segment(asm_text)
    if not isinstance(segment, bytes):
        return False
    assert len(segment) == 2 * (1 << 16)  # 64K two-byte words
    with open(outfile, "wb") as fp:
        fp.write(segment)
    return True


def run(argv):
    if len(argv) != 3:
        print(
            f"Usage: {argv[0]} /path/to/input.asm /path/to/output.segment",
            file=sys.stderr,
        )
        exit(1)
    if not run_on_files(argv[1], argv[2]):
        exit(1)


if __name__ == "__main__":
    run(sys.argv)
