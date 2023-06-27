#!/usr/bin/env python3

from enum import Enum
import difflib
import hashlib
import sys

SEGMENT_LENGTH = 131072
ASM_COMMANDS = dict()
DEBUG_OUTPUT = False
VALID_HEX = "0123456789ABCDEFabcdef"


def mod_s16(value):
    return (value + 0x8000) % 0x1_0000 - 0x8000


def asm_command(fn):
    name = fn.__name__
    prefix = "parse_command_"
    assert name.startswith(prefix), name
    command_name = name[len(prefix) :]
    assert command_name not in ASM_COMMANDS
    ASM_COMMANDS[command_name] = fn
    return fn


def asm_directive(fn):
    name = fn.__name__
    prefix = "parse_directive_"
    assert name.startswith(prefix), name
    command_name = "." + name[len(prefix) :]
    assert command_name not in ASM_COMMANDS
    ASM_COMMANDS[command_name] = fn
    return fn


class ArgType(Enum):
    REGISTER = 1
    IMMEDIATE = 2
    LABEL = 3


class Recursion:
    def __init__(self, assembler, spoofed_lineno, spoofed_pointer):
        self.assembler = assembler
        self.lineno = spoofed_lineno
        self.pointer = spoofed_pointer
        self.is_entered = False

    def do_switch(self):
        self.assembler.current_lineno, self.lineno = (
            self.lineno,
            self.assembler.current_lineno,
        )
        self.assembler.current_pointer, self.pointer = (
            self.pointer,
            self.assembler.current_pointer,
        )

    def __enter__(self):
        assert not self.is_entered  # Not re-entrant
        self.is_entered = True
        self.do_switch()
        # Forbid "with … as …"
        return None

    def __exit__(self, _type, _value, _traceback):
        assert self.is_entered
        self.is_entered = False
        self.do_switch()


class ForwardReference:
    def __init__(self, assembler, by_words, bound_method, data):
        self.assembler = assembler
        self.by_words = by_words
        self.bound_method = bound_method
        self.orig_lineno = assembler.current_lineno
        self.orig_pointer = assembler.current_pointer
        self.data = data

    def resolve_afterwards(self):
        with Recursion(self.assembler, self.orig_lineno, self.orig_pointer):
            return self.apply()

    def apply(self):
        assert self.assembler.current_lineno == self.orig_lineno
        assert self.assembler.current_pointer == self.orig_pointer
        # FIXME: Test two-word patches across the 0xFFFF boundary.
        result = self.bound_method(*self.data)
        if result:
            word_diff = self.assembler.current_pointer - self.orig_pointer
            actual_words = word_diff % 0x1_0000
            assert actual_words == self.by_words, (
                actual_words,
                self.by_words,
                self.bound_method,
                self.data,
                self.orig_pointer,
                self.assembler.current_pointer,
            )
        return result


class Assembler:
    def __init__(self):
        self.segment_words = [None] * (SEGMENT_LENGTH // 2)
        self.current_lineno = None
        self.current_pointer = 0x0000
        self.unused_labels = set()
        # Values are (destination_offset, destination_lineno):
        self.known_labels = dict()
        # Values are lists of ForwardReference instances:
        self.forward_references = dict()
        self.error_log = []
        self.expect_hash = None  # Or tuple (line, SHA256 hex)

    def error(self, msg):
        self.error_log.append(f"line {self.current_lineno}: {msg}")
        return False

    def advance(self, by_words):
        self.current_pointer += by_words
        unwrapped_pointer = self.current_pointer
        self.current_pointer %= SEGMENT_LENGTH // 2
        if unwrapped_pointer != self.current_pointer:
            self.error(
                f"segment pointer overflow, now at 0x{self.current_pointer:04X} (non-fatal)"
            )
            # Not really an error though.
        return True

    def push_word(self, word):
        if DEBUG_OUTPUT:
            print(f"  pushing {word:04X}")
        assert 0 <= word <= 0xFFFF
        if self.segment_words[self.current_pointer] is not None:
            return self.error(
                f"Attempted to overwrite word 0x{self.segment_words[self.current_pointer]:04X} at 0x{self.current_pointer:04X} with 0x{word:04X}."
            )
        self.segment_words[self.current_pointer] = word
        self.advance(1)
        return True

    def push_words(self, *words):
        for word in words:
            if not self.push_word(word):
                return False
        return True

    def forward(self, by_words, label_name, bound_method, data):
        assert by_words < 4096, (
            "most definitely an error, aborting",
            by_words,
            label_name,
            bound_method,
            data,
        )
        fwd_ref = ForwardReference(self, by_words, bound_method, data)
        if label_name in self.known_labels:
            # Immediate resolution
            self.unused_labels.discard(label_name)
            return fwd_ref.apply()
        # Must be skipped for now, to be patched when 'label_name' is defined
        if label_name not in self.forward_references:
            self.forward_references[label_name] = [fwd_ref]
        else:
            self.forward_references[label_name].append(fwd_ref)
        self.advance(by_words)
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
        if not (-0x8000 <= number <= 0xFFFF):
            self.error(
                f"Immediate value {number} (hex: {number:+05X}) in {context} is out of bounds [-0x8000, 0xFFFF]"
            )
            return None
        return number

    def parse_label(self, label_name, context):
        if label_name[0] != "_" or len(label_name) < 2:
            self.error(
                f"Label name for {context} must start with a '_' and contain"
                f" at least two characters, found name '{label_name}' instead"
            )
            return None
        special_chars = "$%&()='\"[]"
        if any(c in label_name for c in special_chars):
            self.error(
                f"Label name for {context} must not contain any special characters"
                f" ({special_chars}), found name '{label_name}' instead"
            )
            return None
        return label_name

    def parse_some(self, accepted_types, reg_or_imm_string, context):
        old_error_log = self.error_log
        self.error_log = []
        keep_new_errors = False
        try:
            if ArgType.REGISTER in accepted_types:
                reg = self.parse_reg(reg_or_imm_string, context)
                if reg is not None:
                    return (ArgType.REGISTER, reg)
            if ArgType.IMMEDIATE in accepted_types:
                imm = self.parse_imm(reg_or_imm_string, context)
                if imm is not None:
                    return (ArgType.IMMEDIATE, imm)
            if ArgType.LABEL in accepted_types:
                label_name = self.parse_label(reg_or_imm_string, context)
                if label_name is not None:
                    return (ArgType.LABEL, label_name)
            keep_new_errors = True
            return None
        finally:
            new_error_log = self.error_log
            self.error_log = old_error_log
            if keep_new_errors:
                assert new_error_log
                self.error_log.extend(new_error_log)

    def parse_reg_or_imm(self, reg_or_imm_string, context):
        return self.parse_some(
            (ArgType.REGISTER, ArgType.IMMEDIATE), reg_or_imm_string, context
        )

    def parse_reg_or_lab(self, reg_or_lab_string, context):
        return self.parse_some(
            (ArgType.REGISTER, ArgType.LABEL), reg_or_lab_string, context
        )

    def parse_imm_or_lab(self, imm_or_lab_string, context):
        return self.parse_some(
            (ArgType.IMMEDIATE, ArgType.LABEL), imm_or_lab_string, context
        )

    def parse_reg_or_imm_or_lab(self, arg_string, context):
        return self.parse_some(
            (ArgType.REGISTER, ArgType.IMMEDIATE, ArgType.LABEL),
            arg_string,
            context,
        )

    def parse_unary_regs_to_byte(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if arg_list == [""]:
            self.error(
                f"Command '{command}' expects either one or two register arguments, got none instead."
            )
            return None
        if not (1 <= len(arg_list) <= 2):
            self.error(
                f"Command '{command}' expects either one or two register arguments, got {arg_list} instead."
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

    def parse_binary_regs_to_byte(self, command, args, allow_duplicate):
        # In case of sub, div, mod, etc. the usual argument order is just stupid.
        # So we change it for *all* binary commands, and also use a different separator
        # to ensure that the user notices the "unusual" order, specifically the space character.
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
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
        if not allow_duplicate and reg_list[0] == reg_list[1]:
            self.error(
                f"Command '{command}' requires two different registers to be used, got {arg_list} instead."
            )
            return None
        return (reg_list[0] << 4) | reg_list[1]

    def binary_command(self, command, args, high_byte, allow_duplicate=True):
        assert high_byte & 0x00FF == 0
        assert high_byte & 0xFF00 != 0
        registers_byte = self.parse_binary_regs_to_byte(command, args, allow_duplicate)
        if registers_byte is None:
            # Error already reported
            return False
        return self.push_word(high_byte | registers_byte)

    @asm_command
    def parse_command_ret(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102A)

    @asm_command
    def parse_command_ill(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0xFFFF)

    @asm_command
    def parse_command_cpuid(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102B)

    @asm_command
    def parse_command_debug(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102C)

    @asm_command
    def parse_command_time(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x102D)

    @asm_command
    def parse_command_sw(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two comma-separated arguments, got {arg_list} instead."
            )
        # TODO: Support immediates?
        addr_register = self.parse_reg(arg_list[0], f"first argument to {command}")
        if addr_register is None:
            # Error already reported
            return False
        value_register = self.parse_reg(arg_list[1], f"second argument to {command}")
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
                f"Command '{command}' expects exactly two arguments, got {arg_list} instead."
            )
        # TODO: Support immediate address
        # TODO: Support labels
        # TODO: Support labels with offset
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
        if addr[0] == ArgType.IMMEDIATE:
            imm_value = addr[1]
            assert 0 <= value_register < 16
            assert -0x8000 <= imm_value <= 0xFFFF
            if -0x80 <= imm_value <= 0x7F or 0xFF80 <= imm_value <= 0xFFFF:
                return self.push_word(
                    0x3000 | (value_register << 8) | (imm_value & 0xFF)
                )
            low_byte = imm_value & 0xFF
            high_byte = (imm_value & 0xFF00) >> 8
            return self.push_words(
                0x3000 | (value_register << 8) | low_byte,
                0x4000 | (value_register << 8) | high_byte,
            )
        raise AssertionError(f"Unexpected argtype {addr[0]} in {addr}")

    @asm_command
    def parse_command_lwi(self, command, args):
        arg_list = [e.strip() for e in args.split(",")]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two arguments, got {arg_list} instead."
            )
        # TODO: Support immediate address
        value_register = self.parse_reg(arg_list[0], f"first argument to {command}")
        if value_register is None:
            # Error already reported
            return False
        addr_register = self.parse_reg(arg_list[1], f"second argument to {command}")
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
                f"Command '{command}' expects exactly two arguments, got {arg_list} instead."
            )
        register = self.parse_reg(arg_list[0], f"first argument to {command}")
        if register is None:
            # Error already reported
            return False
        immediate = self.parse_imm(arg_list[1], f"second argument to {command}")
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
        reg1 = registers_byte >> 4
        reg2 = registers_byte & 0x000F
        if reg1 == reg2:
            return self.error(
                "Refusing noop-mov: This does nothing, and is likely an error."
                f" Use '.word 5F{reg1:X}{reg2:X}' or 'nop' instead."
            )
        return self.push_word(0x5F00 | registers_byte)

    @asm_command
    def parse_command_nop(self, command, args):
        if args != "":
            return self.error(
                f"Command '{command}' does not take any arguments (expected end of line, found '{args}' instead)"
            )
        return self.push_word(0x5F00)

    @asm_command
    def parse_command_add(self, command, args):
        return self.binary_command(command, args, 0x6000)

    @asm_command
    def parse_command_sub(self, command, args):
        return self.binary_command(command, args, 0x6100)

    @asm_command
    def parse_command_mul(self, command, args):
        return self.binary_command(command, args, 0x6200)

    @asm_command
    def parse_command_mulh(self, command, args):
        return self.binary_command(command, args, 0x6300)

    @asm_command
    def parse_command_divu(self, command, args):
        return self.binary_command(command, args, 0x6400)

    @asm_command
    def parse_command_divs(self, command, args):
        return self.binary_command(command, args, 0x6500)

    @asm_command
    def parse_command_modu(self, command, args):
        return self.binary_command(command, args, 0x6600)

    @asm_command
    def parse_command_mods(self, command, args):
        return self.binary_command(command, args, 0x6700)

    @asm_command
    def parse_command_and(self, command, args):
        return self.binary_command(command, args, 0x6800)

    @asm_command
    def parse_command_or(self, command, args):
        return self.binary_command(command, args, 0x6900)

    @asm_command
    def parse_command_xor(self, command, args):
        return self.binary_command(command, args, 0x6A00)

    @asm_command
    def parse_command_sl(self, command, args):
        return self.binary_command(command, args, 0x6B00)

    @asm_command
    def parse_command_srl(self, command, args):
        return self.binary_command(command, args, 0x6C00)

    @asm_command
    def parse_command_sra(self, command, args):
        return self.binary_command(command, args, 0x6D00)

    # TODO: When the VM implements the instruction "exp", implement it here (0x6E__)
    # TODO: When the VM implements the instruction "root", implement it here (0x6F__)

    # cmp is too powerful to make sense. Instead of offloading the work of translating
    # the flags to meaning to the user, do it here in the form of enumeration:
    # LEGS=000_ => No, use "lw rx, 0" instead.
    # LEGS=001_ => Yes, name it "gt".
    # LEGS=010_ => Yes, name it "eq".
    # LEGS=011_ => Yes, name it "ge".
    # LEGS=100_ => Yes, name it "lt".
    # LEGS=101_ => Yes, name it "ne".
    # LEGS=110_ => Yes, name it "le".
    # LEGS=111_ => No, use "lw rx, 1" instead.
    # The instructions gt, ge, lt, le have signed variants (gts, ges, lts, les).
    # The other signed variants don't really make sense (e.g. signed equality).
    # Also, we re-use the "binary_command" method because "lt r4 r5" really should mean "is r4 < r5?"

    @asm_command
    def parse_command_gt(self, command, args):
        return self.binary_command(command, args, 0x8200, False)

    @asm_command
    def parse_command_eq(self, command, args):
        return self.binary_command(command, args, 0x8400, False)

    @asm_command
    def parse_command_ge(self, command, args):
        return self.binary_command(command, args, 0x8600, False)

    @asm_command
    def parse_command_lt(self, command, args):
        return self.binary_command(command, args, 0x8800, False)

    @asm_command
    def parse_command_ne(self, command, args):
        return self.binary_command(command, args, 0x8A00, False)

    @asm_command
    def parse_command_le(self, command, args):
        return self.binary_command(command, args, 0x8C00, False)

    @asm_command
    def parse_command_gts(self, command, args):
        return self.binary_command(command, args, 0x8300, False)

    @asm_command
    def parse_command_ges(self, command, args):
        return self.binary_command(command, args, 0x8700, False)

    @asm_command
    def parse_command_lts(self, command, args):
        return self.binary_command(command, args, 0x8900, False)

    @asm_command
    def parse_command_les(self, command, args):
        return self.binary_command(command, args, 0x8D00, False)

    def compare_zero_command(self, command, args, high_byte):
        assert 0xFF00 & high_byte != 0 and 0x00FF & high_byte == 0
        if not args or " " in args:
            return self.error(
                f"Command '{command}' expects exactly one register arguments, got {args} instead."
            )
        test_reg = self.parse_reg(args, f"first argument to {command}")
        if test_reg is None:
            # Error already reported
            return False
        return self.push_word(high_byte | (test_reg << 4) | test_reg)

    # FIXME: Should not be advertised during misspellings.
    @asm_command
    def parse_command_gtz(self, command, _args):
        # Intentionally don't implement "gtz rX", as it is identical to "nez rX".
        # Make sure that the user learns about both "gtzs" and "nez".
        return self.error(
            f"Refusing hypothetical '{command}' pseudo-instruction, because there is no unsigned"
            " integer less than zero. Consider 'gtsz' for signed comparison, or 'nez' to check for"
            " inequality with zero."
        )

    @asm_command
    def parse_command_eqz(self, command, args):
        return self.compare_zero_command(command, args, 0x8400)

    # Intentionally don't implement "gez rX", as it is identical to "lw rX, 1".
    # "gezs" should be automatically among the suggestions.
    # Intentionally don't implement "ltz rX", as it is identical to "lw rX, 0".
    # "ltzs" should be automatically among the suggestions.

    @asm_command
    def parse_command_nez(self, command, args):
        return self.compare_zero_command(command, args, 0x8A00)

    # FIXME: Should not be advertised during misspellings.
    @asm_command
    def parse_command_lez(self, command, _args):
        # Intentionally don't implement "lez rX", as it is identical to "eqz rX".
        # Make sure that the user learns about both "lezs" and "eqz".
        return self.error(
            f"Refusing hypothetical '{command}' pseudo-instruction, because there is no unsigned"
            " integer less than zero. Consider 'lesz' for signed comparison, or 'eqz' to check for"
            " equality with zero."
        )

    @asm_command
    def parse_command_gtsz(self, command, args):
        return self.compare_zero_command(command, args, 0x8300)

    @asm_command
    def parse_command_gesz(self, command, args):
        return self.compare_zero_command(command, args, 0x8700)

    @asm_command
    def parse_command_ltsz(self, command, args):
        return self.compare_zero_command(command, args, 0x8900)

    @asm_command
    def parse_command_lesz(self, command, args):
        return self.compare_zero_command(command, args, 0x8D00)

    def branch_pseudo_command(self, compare_mask, command, args):
        assert (compare_mask & 0xF0FF) == 0 and (
            compare_mask & 0x0F00
        ) != 0, compare_mask
        arg_list = [e.strip() for e in args.split(" ", 2)]
        if len(arg_list) != 3:
            self.error(
                f"Command '{command}' expects exactly three space-separated arguments (reg reg imm_or_lab), got {arg_list} instead."
            )
            return False
        # In case some maniac writes more than one space, like "bne  r4  r5  r6":
        # FIXME: Doesn't quite work for three args!
        arg_list[1] = arg_list[1].strip()
        reg_lhs = self.parse_reg(arg_list[0], f"first argument to {command}")
        reg_rhs_dest = self.parse_reg(arg_list[1], f"second argument to {command}")
        if reg_lhs is None or reg_rhs_dest is None:
            # Error already reported
            return False
        if not self.push_word(0x8000 | compare_mask | (reg_lhs << 4) | reg_rhs_dest):
            # Error already reported
            return False
        return self.emit_branch_to_imm_or_lab(
            command, reg_rhs_dest, arg_list[2], f"third argument to {command}"
        )

    @asm_command
    def parse_command_bgt(self, command, args):
        return self.branch_pseudo_command(0x200, command, args)

    @asm_command
    def parse_command_beq(self, command, args):
        return self.branch_pseudo_command(0x400, command, args)

    @asm_command
    def parse_command_bge(self, command, args):
        return self.branch_pseudo_command(0x600, command, args)

    @asm_command
    def parse_command_blt(self, command, args):
        return self.branch_pseudo_command(0x800, command, args)

    @asm_command
    def parse_command_bne(self, command, args):
        return self.branch_pseudo_command(0xA00, command, args)

    @asm_command
    def parse_command_ble(self, command, args):
        return self.branch_pseudo_command(0xC00, command, args)

    @asm_command
    def parse_command_bgts(self, command, args):
        return self.branch_pseudo_command(0x300, command, args)

    @asm_command
    def parse_command_bges(self, command, args):
        return self.branch_pseudo_command(0x700, command, args)

    @asm_command
    def parse_command_blts(self, command, args):
        return self.branch_pseudo_command(0x900, command, args)

    @asm_command
    def parse_command_bles(self, command, args):
        return self.branch_pseudo_command(0xD00, command, args)

    def emit_branch_to_imm_or_lab(self, command, condition_reg, raw_arg, arg_name):
        imm_or_lab = self.parse_imm_or_lab(raw_arg, arg_name)
        if imm_or_lab is None:
            # Error already reported
            return False
        if imm_or_lab[0] == ArgType.IMMEDIATE:
            offset_value = imm_or_lab[1]
            return self.emit_b_by_value(command, condition_reg, offset_value)
        if imm_or_lab[0] == ArgType.LABEL:
            label_name = imm_or_lab[1]
            call_data = (command, condition_reg, label_name)
            return self.forward(1, label_name, self.emit_b_to_label, call_data)
        raise AssertionError(f"imm_or_lab returned '{imm_or_lab}'?! ")

    def emit_long_branch_inverted_to_imm_or_lab(
        self, command, inverted_condition_reg, raw_arg, arg_name, allow_short
    ):
        imm_or_lab = self.parse_imm_or_lab(raw_arg, arg_name)
        if imm_or_lab is None:
            # Error already reported
            return False
        # "b reg_inverted +2" → Jump over the following instruction if the inverted condition is true.
        # (I.e. if the original condition is false.)
        if not self.emit_b_by_value(command, inverted_condition_reg, 2):
            # Error already reported
            return False
        # "j imm_or_lab_destination" → Jump to the destination.
        if imm_or_lab[0] == ArgType.IMMEDIATE:
            offset_value = imm_or_lab[1]
            return self.emit_j_by_offset(command, offset_value, allow_short)
        if imm_or_lab[0] == ArgType.LABEL:
            label_name = imm_or_lab[1]
            # TODO: Support additional offset?
            call_data = (command, label_name, 0, allow_short)
            return self.forward(1, label_name, self.emit_j_to_label, call_data)
        raise AssertionError(f"imm_or_lab returned '{imm_or_lab}'?! ")
        # In other words, this entire method emits the code:
        #     if (!condition)
        #         goto _afterwards;
        #     goto _destination;
        #     _afterwards:
        # This is useful because this allows us to do a "medium-length jump" of 12 bits in just *two* instructions.
        # This is more lightweight than doing a full "b +6; lw reg_foo imm_address; j reg_foo;", which is *four* instructions.

    def branch_zero_pseudo_command(self, compare_mask, command, args):
        assert (compare_mask & 0xF0FF) == 0 and (
            compare_mask & 0x0F00
        ) != 0, compare_mask
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "add r4  r5":
        arg_list[1] = arg_list[1].strip()
        value_reg = self.parse_reg(arg_list[0], f"first argument to {command}")
        if value_reg is None:
            # Error already reported
            return False
        if not self.push_word(0x8000 | compare_mask | (value_reg << 4) | value_reg):
            # Error already reported
            return False
        # FIXME: Support labels with offset
        return self.emit_branch_to_imm_or_lab(
            command, value_reg, arg_list[1], f"second argument to {command}"
        )

    @asm_command
    def parse_command_beqz(self, command, args):
        return self.branch_zero_pseudo_command(0x400, command, args)

    @asm_command
    def parse_command_bnez(self, command, args):
        # Optimization: Don't call branch_zero_pseudo_command here, because we don't need to prepare/compare the reg_value at all.
        return self.parse_command_b(command, args)

    @asm_command
    def parse_command_bgtsz(self, command, args):
        return self.branch_zero_pseudo_command(0x300, command, args)

    @asm_command
    def parse_command_bgesz(self, command, args):
        return self.branch_zero_pseudo_command(0x700, command, args)

    @asm_command
    def parse_command_bltsz(self, command, args):
        return self.branch_zero_pseudo_command(0x900, command, args)

    @asm_command
    def parse_command_blesz(self, command, args):
        return self.branch_zero_pseudo_command(0xD00, command, args)

    def emit_b_by_value(self, command, condition_reg, offset_value):
        if offset_value >= 0xFF80:
            return self.error(
                f"Ambiguous offset 0x{offset_value:04X} to command '{command}': Try a value in [-128, 129] instead."
            )
        if not (-128 <= offset_value <= 129):
            return self.error(
                f"Command '{command}' can only branch by offsets in [-128, 129], but not by {offset_value}."
                " Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
            )
        if offset_value == 0:
            return self.error(
                f"Command '{command}' cannot encode an infinite loop (offset 0). Try using 'j reg' instead."
            )
        if offset_value == 1:
            return self.error(
                f"Command '{command}' cannot encode the nop-branch (offset 1). Try using 'nop' instead."
            )
        if offset_value < 0:
            sign_mask = 0x80
            offset_value = -offset_value - 1
        else:
            assert offset_value > 0
            sign_mask = 0x00
            offset_value = offset_value - 2
        assert 0 <= offset_value <= 0x7F
        return self.push_word(0x9000 | (condition_reg << 8) | sign_mask | offset_value)

    def emit_b_to_label(self, command, condition_reg, label_name):
        destination_offset, destination_lineno = self.known_labels[label_name]
        self.unused_labels.discard(label_name)
        offset_value = mod_s16(destination_offset - self.current_pointer)
        return self.emit_b_by_value(
            f"{command} (to label {label_name}=0x{destination_offset:04X}, defined in line {destination_lineno})",
            condition_reg,
            offset_value,
        )

    @asm_command
    def parse_command_b(self, command, args):
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "add r4  r5":
        arg_list[1] = arg_list[1].strip()
        condition_reg = self.parse_reg(arg_list[0], f"first argument to {command}")
        if condition_reg is None:
            # Error already reported
            return False
        # FIXME: Support labels with offset
        # FIXME: Support long branches?
        return self.emit_branch_to_imm_or_lab(
            command, condition_reg, arg_list[1], f"second argument to {command}"
        )

    @asm_command
    def parse_command_lb(self, command, args):
        arg_list = [e.strip() for e in args.split(" ", 1)]
        # FIXME: Only emit this once per compilation unit.
        self.error(
            f"Command '{command}' inverts the condition register, and ends up needing three instructions."
            " Consider using a combined longbranch-compare instead (e.g. lbles)."
        )
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "add r4  r5":
        arg_list[1] = arg_list[1].strip()
        condition_reg = self.parse_reg(arg_list[0], f"first argument to {command}")
        if condition_reg is None:
            # Error already reported
            return False
        # "eqz condition_reg"
        # That's essentially a boolean inversion.
        # FIXME: Make "boolconv" and "boolnot" aliases of "nez" and "eqz", respectively.
        if not self.push_word(0x8400 | (condition_reg << 4) | condition_reg):
            # Error already reported
            return False
        # This inversion is inefficient, because the condition probably comes from a comparison right before the "lb".
        # Hence the urging to use shorthands like lbles, which have built-in negation.
        return self.emit_long_branch_inverted_to_imm_or_lab(
            command,
            condition_reg,
            arg_list[1],
            f"second argument to {command}",
            allow_short=False,
        )

    def parse_command_lb_cmp_tworeg(self, uninverted_compare_mask, command, args):
        assert (uninverted_compare_mask & 0xF0FF) == 0 and (
            uninverted_compare_mask & 0x0F00
        ) != 0, uninverted_compare_mask
        arg_list = [e.strip() for e in args.split(" ", 2)]
        if len(arg_list) != 3:
            return self.error(
                f"Command '{command}' expects exactly three space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "bne  r4  r5  r6":
        # FIXME: Doesn't quite work for three args!
        arg_list[1] = arg_list[1].strip()
        reg_lhs = self.parse_reg(arg_list[0], f"first argument to {command}")
        reg_rhs_dest = self.parse_reg(arg_list[1], f"second argument to {command}")
        if reg_lhs is None or reg_rhs_dest is None:
            # Error already reported
            return False
        # Invert the compare mask by inverting L(ess), E(qual), and G(reater), but not the S(igned) bit:
        compare_mask = 0x0E00 ^ uninverted_compare_mask
        if not self.push_word(0x8000 | compare_mask | (reg_lhs << 4) | reg_rhs_dest):
            # Error already reported
            return False
        return self.emit_long_branch_inverted_to_imm_or_lab(
            command,
            reg_rhs_dest,
            arg_list[2],
            f"third argument to {command}",
            allow_short=False,
        )
        # Overall, this method folds the inversion necessary for the "medium-length branch" into the
        # comparison instruction, meaning that i.e. lbeq only takes one instruction more than beq.

    @asm_command
    def parse_command_lbeq(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0400, command, args)

    @asm_command
    def parse_command_lbne(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0A00, command, args)

    @asm_command
    def parse_command_lblt(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0800, command, args)

    @asm_command
    def parse_command_lble(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0C00, command, args)

    @asm_command
    def parse_command_lbgt(self, command, args):  # 🏳️‍🌈, kinda
        return self.parse_command_lb_cmp_tworeg(0x0200, command, args)

    @asm_command
    def parse_command_lbge(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0600, command, args)

    @asm_command
    def parse_command_lblts(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0900, command, args)

    @asm_command
    def parse_command_lbles(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0D00, command, args)

    @asm_command
    def parse_command_lbgts(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0300, command, args)

    @asm_command
    def parse_command_lbges(self, command, args):
        return self.parse_command_lb_cmp_tworeg(0x0700, command, args)

    def parse_command_lb_cmp_zero(self, uninverted_compare_mask, command, args):
        assert (uninverted_compare_mask & 0xF0FF) == 0 and (
            uninverted_compare_mask & 0x0F00
        ) != 0, uninverted_compare_mask
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "bne  r4  r5  r6":
        # FIXME: Doesn't quite work!
        arg_list[1] = arg_list[1].strip()
        reg_value = self.parse_reg(arg_list[0], f"first argument to {command}")
        if reg_value is None:
            # Error already reported
            return False
        # Invert the compare mask by inverting L(ess), E(qual), and G(reater), but not the S(igned) bit:
        compare_mask = 0x0E00 ^ uninverted_compare_mask
        if not self.push_word(0x8000 | compare_mask | (reg_value << 4) | reg_value):
            # Error already reported
            return False
        return self.emit_long_branch_inverted_to_imm_or_lab(
            command,
            reg_value,
            arg_list[1],
            f"second argument to {command}",
            allow_short=False,
        )
        # Overall, this method folds the inversion necessary for the "medium-length branch" into the
        # comparison instruction, meaning that i.e. lbltsz only takes one instruction more than bltsz.

    @asm_command
    def parse_command_lbeqz(self, command, args):
        # Optimization: Don't call parse_command_lb_cmp_zero, because we don't need to prepare/compare the reg_value at all.
        arg_list = [e.strip() for e in args.split(" ", 1)]
        if len(arg_list) != 2:
            return self.error(
                f"Command '{command}' expects exactly two space-separated register arguments, got {arg_list} instead."
            )
        # In case some maniac writes more than one space, like "lbeqz r4  r5":
        # FIXME: Doesn't quite work!
        arg_list[1] = arg_list[1].strip()
        reg_value = self.parse_reg(arg_list[0], f"first argument to {command}")
        if reg_value is None:
            # Error already reported
            return False
        # Intentionally emit no comparison instruction here.
        return self.emit_long_branch_inverted_to_imm_or_lab(
            command,
            reg_value,
            arg_list[1],
            f"second argument to {command}",
            allow_short=False,
        )

    @asm_command
    def parse_command_lbnez(self, command, args):
        return self.parse_command_lb_cmp_zero(0x0A00, command, args)

    @asm_command
    def parse_command_lbltsz(self, command, args):
        return self.parse_command_lb_cmp_zero(0x0900, command, args)

    @asm_command
    def parse_command_lblesz(self, command, args):
        return self.parse_command_lb_cmp_zero(0x0D00, command, args)

    @asm_command
    def parse_command_lbgtsz(self, command, args):
        return self.parse_command_lb_cmp_zero(0x0300, command, args)

    @asm_command
    def parse_command_lbgesz(self, command, args):
        return self.parse_command_lb_cmp_zero(0x0700, command, args)

    def command_j_register(self, register, offset):
        if offset >= 0xFF80:
            return self.error(
                f"Ambiguous offset 0x{offset:04X} to command 'j'. Note that this value is relative and signed."
            )
        if not (-0x80 <= offset <= 0x7F):
            return self.error(
                f"Command 'j' can only branch by offsets in [-128, 127], but not by {offset}."
                " Try manually loading the final address into a register first."
            )
        offset_byte = offset & 0xFF
        return self.push_word(0xB000 | (register << 8) | offset_byte)

    def emit_j_by_offset(self, command, offset, allow_short):
        assert offset is not None
        if offset >= 0xFF80:
            return self.error(
                f"Ambiguous offset 0x{offset:04X} to command '{command}'. Note that this value is relative."
            )
        if not (-(1 + 0x7FF) <= offset <= (2 + 0x7FF)):
            return self.error(
                f"Command '{command}' can only branch by offsets in [-2048, 2049], but not by {offset}."
                f" Some commands support longer jumps, try 'l{command}' instead."
                " Or try manually loading the address into a register first."
            )
        if offset == 0:
            return self.error(
                f"Command '{command}' cannot encode an infinite loop (offset 0). Try jumping to a register instead."
            )
        if offset == 1:
            return self.error(
                f"Command '{command}' cannot encode the nop-jump (offset 1). Try using 'nop' instead."
            )
        if not allow_short and -118 < offset < 119:
            # Even though anything in the range -128 < offset < 129 can be shortened, we don't want
            # to be too aggressive: Changing the instruction can change several other offsets, and
            # we don't want to force the user into a whack-a-mole game of swapping long-to-short-to-long
            # branches. Hence, leave a slack of ehhh ten instructions I guess.
            return self.error(
                f"Pseudo-instruction '{command}' supports jumps in the range [-2048, 2049], but was"
                f" used for just a short offset of {offset}. Try using the non-long version,"
                " which uses fewer instructions."
            )
        if offset < 0:
            sign_mask = 0x0800
            offset = -offset - 1
        else:
            assert offset > 0
            sign_mask = 0
            offset = offset - 2
        assert 0 <= offset <= 0x7FF
        return self.push_word(0xA000 | sign_mask | offset)

    def emit_j_to_label(self, command, label_name, extra_offset, allow_short):
        destination = self.known_labels[label_name][0] + extra_offset
        self.unused_labels.discard(label_name)
        delta = mod_s16(destination - self.current_pointer)
        pseudo_command = f"{command} (to {label_name} {extra_offset:+} = by {delta:+})"
        return self.emit_j_by_offset(pseudo_command, delta, allow_short)

    def command_j_onearg(self, command, arg):
        if not arg:
            return self.error(
                f"Command '{command}' expects either one or two arguments, got none instead."
            )
        parsed_arg = self.parse_reg_or_imm_or_lab(
            arg, f"first argument of one-arg-{command}"
        )
        if parsed_arg is None:
            return self.error(
                f"Command '{command}' with a single argument expects either immediate, register, or label, got '{arg}' instead."
                " Note that offsets have to use a space, like 'r4 +5'."
            )
        if parsed_arg[0] == ArgType.REGISTER:
            reg = parsed_arg[1]
            return self.command_j_register(reg, 0)
        if parsed_arg[0] == ArgType.IMMEDIATE:
            imm = parsed_arg[1]
            return self.emit_j_by_offset("j", imm, allow_short=True)
        if parsed_arg[0] == ArgType.LABEL:
            label_name = parsed_arg[1]
            call_data = (command, label_name, 0, True)
            return self.forward(1, label_name, self.emit_j_to_label, call_data)
        raise AssertionError(f"Unexpected type {parsed_arg}")

    def command_j_twoarg(self, command, reg_or_lab_string, imm_string):
        reg_or_lab = self.parse_reg_or_lab(
            reg_or_lab_string, f"first argument to two-arg-{command}"
        )
        if reg_or_lab is None:
            return self.error(
                f"Command '{command}' with two arguments expects either register or label for first argument, got '{reg_or_lab_string}' instead."
                " Note that offsets have to use a space, like 'r4 +5'."
            )
        imm = self.parse_imm(imm_string, f"second argument to two-arg-{command}")
        if imm is None:
            # Error already reported
            return False
        if reg_or_lab[0] == ArgType.REGISTER:
            reg = reg_or_lab[1]
            return self.command_j_register(reg, imm)
        if reg_or_lab[0] == ArgType.LABEL:
            label_name = reg_or_lab[1]
            call_data = (command, label_name, imm, True)
            return self.forward(1, label_name, self.emit_j_to_label, call_data)
        raise AssertionError(f"Unexpected type {reg_or_lab}")

    @asm_command
    def parse_command_j(self, command, args):
        args = args.strip()
        arg_parts = args.split(" ", 1)
        if len(arg_parts) == 1:
            return self.command_j_onearg(command, arg_parts[0])
        if len(arg_parts) == 2:
            return self.command_j_twoarg(command, arg_parts[0], arg_parts[1])
        raise AssertionError(f"Wtf .split(, 1) returned {arg_parts}?")

    @asm_directive
    def parse_directive_offset(self, command, args):
        args = args.strip()
        arg_parts = args.split(" ", 1)
        if len(arg_parts) > 1 or not arg_parts[0]:
            return self.error(
                f"Directive '{command}' takes exactly one argument (the new absolute offset), found '{args}' instead"
            )
        new_offset = self.parse_imm_or_lab(arg_parts[0], "argument of .offset")
        if new_offset is None:
            return self.error(
                f"Directive '{command}' takes either an immediate value or a label, found '{arg_parts[0]}' instead"
            )
        if new_offset[0] == ArgType.IMMEDIATE:
            if new_offset[1] < 0:
                return self.error(
                    f"Immediate argument to '{command}' must be positive, found '{args}' instead"
                )
            self.current_pointer = new_offset[1]
        elif new_offset[0] == ArgType.LABEL:
            label_name = new_offset[1]
            if label_name not in self.known_labels:
                self.error(
                    f"Label argument to '{command}' must be an already-delared label, found unknown label '{args}' instead"
                )
                return self.error(
                    f"The already-defined labels are: {sorted(list(self.known_labels.keys()))}"
                )
            self.current_pointer = self.known_labels[label_name][0]
            self.unused_labels.discard(label_name)
        # No codegen
        return True

    @asm_directive
    def parse_directive_word(self, command, args):
        args = args.strip()
        arg_parts = args.split(" ", 1)
        if len(arg_parts) > 1 or not arg_parts[0]:
            return self.error(
                f"Directive '{command}' takes exactly one argument (the literal word), found '{args}' instead"
            )
        value = self.parse_imm(arg_parts[0], f"argument of {command}")
        if value is None:
            # Error was already reported
            return False
        if value < 0:
            value &= 0xFFFF
        return self.push_word(value)

    @asm_directive
    def parse_directive_label(self, command, args):
        args = args.strip()
        arg_parts = args.split(" ", 1)
        if not arg_parts[0]:
            return self.error(
                f"Directive '{command}' takes exactly one argument (the literal label name), found nothing instead"
            )
        if len(arg_parts) > 1 or not arg_parts[0]:
            return self.error(
                f"Directive '{command}' takes exactly one argument (the literal label name), found {arg_parts} instead"
            )
        label_name = self.parse_label(arg_parts[0], "argument of .label")
        if label_name is None:
            # Error already reported
            return False
        if label_name in self.known_labels.keys():
            old_offset, old_line = self.known_labels[label_name]
            return self.error(
                f"Label '{label_name}' previously defined in line {old_line} (old offset 0x{old_offset:04X}, new offset 0x{self.current_pointer:04X})"
            )
        assert label_name not in self.unused_labels
        self.known_labels[label_name] = (self.current_pointer, self.current_lineno)
        old_references = self.forward_references.get(label_name)
        if old_references is not None:
            any_reference_failed = False
            del self.forward_references[label_name]
            for fwd_ref in old_references:
                if not fwd_ref.resolve_afterwards():
                    any_reference_failed = True
            if any_reference_failed:
                return self.error(f"When label {label_name} was defined.")
        else:
            self.unused_labels.add(label_name)
        # No codegen
        return True

    @asm_directive
    def parse_directive_assert_hash(self, command, args):
        hash_hex = args.strip()
        if any(c not in VALID_HEX for c in hash_hex) or len(hash_hex) != 64:
            return self.error(
                f"Argument to {command} must be a single 64-char hexstring of the expected SHA256, found instead '{hash_hex}'."
            )
        assert len(bytes.fromhex(hash_hex)) == 32
        if self.expect_hash is not None:
            return self.error(
                f"Expected hash already stated in line {self.expect_hash[0]}."
            )
        self.expect_hash = (self.current_lineno, hash_hex.upper())
        # No codegen
        return True

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
            suggestions = difflib.get_close_matches(
                command, sorted(list(ASM_COMMANDS.keys()))
            )
            if suggestions:
                plural = "es" if len(suggestions) > 1 else ""
                return self.error(
                    f"Command '{command}' not found. Close match{plural}: {', '.join(suggestions)}"
                )
            return self.error(f"Command '{command}' not found.")

        return command_fn(self, command, args)

    def segment_bytes(self):
        assert len(self.segment_words) == 65536
        has_problem = False
        if self.forward_references:
            error_text = ", ".join(
                f"line {fwd_ref.orig_lineno} at offset {fwd_ref.orig_pointer} references label {label_name}"
                for label_name, fwd_refs in self.forward_references.items()
                for fwd_ref in fwd_refs
            )
            self.error(
                f"Found end of asm text, but some forward references are unresolved: {error_text}"
            )
            self.error(
                f"Did you mean any of these defined labels? {list(self.known_labels.keys())}"
            )
            has_problem = True
        if self.unused_labels:
            error_text = ", ".join(
                f"'{label_name}' (line {label_lineno}, offset {label_offset})"
                for label_name in sorted(self.unused_labels)
                for label_offset, label_lineno in [self.known_labels[label_name]]
            )
            self.error(
                f"Unused label(s), try using them in dead code, or commenting them out: {error_text}"
            )
            has_problem = True
        if has_problem:
            return None
        segment = bytearray(SEGMENT_LENGTH)
        for i, word in enumerate(self.segment_words):
            if word is not None:
                segment[2 * i] = word >> 8
                segment[2 * i + 1] = word & 0xFF
        segment_bytes = bytes(segment)
        if self.expect_hash is not None:
            hash_line, expect_hash_hex = self.expect_hash
            actual_hash_hex = hashlib.sha256(segment_bytes).hexdigest().upper()
            if actual_hash_hex != expect_hash_hex:
                self.error(
                    f"Compilation successful, but encountered hash mismatch: line {hash_line} expects hash {expect_hash_hex}, but created hash {actual_hash_hex} instead."
                )
                return None
        return segment_bytes


def compile_to_segment(asm_text):
    """
    Returns a tuple of (asm_bytes, error_log), where:
    - asm_bytes is an instance of 'bytes' (in case of success) or is 'None' (in case of failure).
    - error_log is an instance of 'list', containing a list of warning and error message strings.
    """
    asm = Assembler()
    for i, line in enumerate(asm_text.split("\n")):
        if not asm.parse_line(line, i + 1):
            return None, asm.error_log
    return asm.segment_bytes(), asm.error_log


def run_on_files(infile, outfile):
    with open(infile, "r") as fp:
        asm_text = fp.read()
    segment, error_log = compile_to_segment(asm_text)
    for e in error_log:
        print(e, file=sys.stderr)
    if segment is None:
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
