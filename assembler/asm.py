#!/usr/bin/env python3

from enum import Enum
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


class ArgType(Enum):
    REGISTER = 1
    IMMEDIATE = 2


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

    def push_words(self, *words):
        for word in words:
            if not self.push_word(word):
                return False
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

    def parse_imm(self, imm_string, context):
        # TODO: Add value alias support?
        # TODO: Add inline-expression support?
        try:
            # "Base 0" automatically handles base detection, yay!
            number = int(imm_string, 0)
        except ValueError:
            self.error(
                f"Cannot parse immediate for {context}: Expected integer number, "
                f"instead got '{imm_string}'. Try something like '42', '0xABCD', or '-0x123' instead."
            )
            return None
        return number

    def parse_reg_or_imm(self, reg_or_imm_string, context):
        # ArgType
        reg = self.parse_reg(reg_or_imm_string, context)
        if reg is not None:
            return (ArgType.REGISTER, reg)
        # FIXME: Shouldn't report the error message about it not being a register just yet
        imm = self.parse_imm(reg_or_imm_string, context)
        if imm is None:
            return None
        if not (-0x8000 <= imm <= 0xFFFF):
            self.error(
                f"Immediate value {imm} (hex: {imm:+05X}) is out out bounds [-0x8000, 0xFFFF]"
            )
            return None
        return (ArgType.IMMEDIATE, imm)

    def parse_unary_regs_to_byte(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if not (1 <= len(arg_list) <= 2):
            self.error(
                f"Command '{command}' expects either one or two register arguments, got '{arg_list}' instead."
            )
            return None
        reg_list = []
        for i, arg in enumerate(arg_list):
            register = self.parse_reg(
                arg, f"argument #{i + 1} (1-indexed) to {command}"
            )
            if register is None:
                # Error already reported
                return None
            reg_list.append(register)
        # Unary functions can be applied in-place, allow this as a short-hand for it.
        # Example: "decr r5" instead of "decr r5, r5"
        if len(reg_list) == 1:
            reg_list.append(reg_list[0])
        assert len(reg_list) == 2
        # "decr r1, r2" means that we write into r1, by convention of always writing into the first-mentioned register.
        # The ISA defines that the written-to register is in the least-significant bits.
        # I probably fucked up the definitions there, but I'm too lazy to change it now.
        return (reg_list[1] << 4) | reg_list[0]

    def parse_binary_regs_to_byte(self, command, args):
        # In case of sub, div, mod, etc. the usual argument order is just stupid.
        # So we change it for *all* binary commands, and also use a different separator
        # to ensure that the user notices the "unusual" order, specifically the space character.
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got '{arg_list}' instead."
            )
            return None
        # In case some maniac writes more than one space, like "add r4  r5":
        arg_list[1] = arg_list[1].strip()
        reg_list = []
        for i, arg in enumerate(arg_list):
            register = self.parse_reg(
                arg, f"argument #{i + 1} (1-indexed) to {command}"
            )
            if register is None:
                # Error already reported
                return None
            reg_list.append(register)
        assert len(reg_list) == 2
        return (reg_list[0] << 4) | reg_list[1]

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

    @asm_command
    def parse_command_lw(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command 'lw' expects exactly two arguments, got '{arg_list}' instead."
            )
        # TODO: Support immediate address
        value_register = self.parse_reg(arg_list[0], "first argument to lw")
        if value_register is None:
            # Error already reported
            return False
        addr = self.parse_reg_or_imm(arg_list[1], "second argument to lw")
        if addr is None:
            # Error already reported
            return False
        if addr[0] == ArgType.REGISTER:
            addr_register = addr[1]
            assert 0 <= value_register < 16
            assert 0 <= addr_register < 16
            return self.push_word(0x2100 | (addr_register << 4) | value_register)
        elif addr[0] == ArgType.IMMEDIATE:
            imm_value = addr[1]
            assert 0 <= value_register < 16
            assert -0x8000 <= imm_value <= 0xFFFF
            if -0x80 <= imm_value <= 0x7F or 0xFF80 <= imm_value <= 0xFFFF:
                return self.push_word(
                    0x3000 | (value_register << 8) | (imm_value & 0xFF)
                )
            else:
                low_byte = imm_value & 0xFF
                high_byte = (imm_value & 0xFF00) >> 8
                return self.push_words(
                    0x3000 | (value_register << 8) | low_byte,
                    0x4000 | (value_register << 8) | high_byte,
                )
        else:
            raise AssertionError(f"Unexpected argtype {addr[0]} in {addr}")

    @asm_command
    def parse_command_lwi(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command 'lwi' expects exactly two arguments, got '{arg_list}' instead."
            )
        # TODO: Support immediate address
        value_register = self.parse_reg(arg_list[0], "first argument to lwi")
        if value_register is None:
            # Error already reported
            return False
        addr_register = self.parse_reg(arg_list[1], "second argument to lwi")
        if addr_register is None:
            # Error already reported
            return False
        assert 0 <= addr_register < 16
        assert 0 <= value_register < 16
        return self.push_word(0x2200 | (addr_register << 4) | value_register)

    @asm_command
    def parse_command_lhi(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command 'lhi' expects exactly two arguments, got '{arg_list}' instead."
            )
        register = self.parse_reg(arg_list[0], "first argument to lhi")
        if register is None:
            # Error already reported
            return False
        immediate = self.parse_imm(arg_list[1], "second argument to lhi")
        if immediate is None:
            # Error already reported
            return False
        if immediate < 0:
            return self.error(
                f"Unsure how to load the high byte of negative word {immediate}. "
                f"Specify the byte as a positive number instead."
            )
        if immediate > 0xFF:
            if immediate & 0xFF == 0:
                immediate >>= 8
            else:
                return self.error(
                    f"Unsure how to load the high byte of a two-byte word 0x{immediate:04X}. "
                    f"Specify the byte either as 0xAB00 or as 0xAB instead."
                )
        assert 0 <= register < 16
        return self.push_word(0x4000 | (register << 8) | immediate)

    @asm_command
    def parse_command_decr(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5800 | registers_byte)

    @asm_command
    def parse_command_incr(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5900 | registers_byte)

    @asm_command
    def parse_command_not(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5A00 | registers_byte)

    @asm_command
    def parse_command_popcnt(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5B00 | registers_byte)

    @asm_command
    def parse_command_clz(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5C00 | registers_byte)

    @asm_command
    def parse_command_ctz(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5D00 | registers_byte)

    @asm_command
    def parse_command_rnd(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5E00 | registers_byte)

    @asm_command
    def parse_command_mov(self, command, args):
        registers_byte = self.parse_unary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x5F00 | registers_byte)

    @asm_command
    def parse_command_nop(self, command, args):
        if args != "":
            return self.error(
                f"Command 'nop' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x5F00)

    @asm_command
    def parse_command_add(self, command, args):
        registers_byte = self.parse_binary_regs_to_byte(command, args)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(0x6000 | registers_byte)

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
