#!/usr/bin/env python3

from collections import Counter
import asm
import unittest

ASM_TESTS = [
    ("empty", "", ""),
    (
        "newline",
        """
        """,
        "0000",
    ),
    (
        "comment",
        """
        # Hello, world!
        """,
        "",
    ),
    (
        "return",
        """
        ret
        """,
        "102A",
    ),
    (
        "inline comment",
        """
        # This is awesome.
        ret  # Return, yo!
        # Hooray!
        """,
        "102A",
    ),
    (
        "inline comment multi",
        """
        ret # Return   # but you knew that already, didn't you?
        """,
        "102A",
    ),
    (
        "illegal",
        """
        ill
        """,
        "FFFF",
    ),
    (
        "more than one instruction",
        """
        ret
        ill
        """,
        "102A FFFF",
    ),
    (
        "CPUID",
        """
        cpuid
        """,
        "102B",
    ),
    (
        "Debug-dump",
        """
        debug
        """,
        "102C",
    ),
    (
        "Time",
        """
        time
        """,
        "102D",
    ),
    (
        "Store word",
        """
        sw r0, r0
        sw r1, r0
        sw r10, r15
        """,
        "2000 2010 20AF",
    ),
    (
        "Load word instruction",
        """
        lwi r0, r0
        lwi r0, r1
        lwi r15, r10
        """,
        "2200 2210 22AF",
    ),
    (
        "Load word data, memory-only",
        """
        lw r0, r0
        lw r0, r1
        lw r15, r10
        """,
        "2100 2110 21AF",
    ),
    (
        "Load word data immediate (single insn)",
        """
        lw r0, 0x0000
        lw r1, -1
        lw r5, 42
        lw r8, 0x7F
        lw r9, 0xFF80
        lw r10, 0xFFFE
        """,
        "3000 31FF 352A 387F 3980 3AFE",
    ),
    (
        "Load word data immediate (double insn)",
        """
        lw r0, 0x0081
        lw r1, -0x81
        lw r2, 0xABCD
        lw r3, 0x1234
        lw r9, 0xFF7F
        """,
        "3081 4000 317F 41FF 32CD 42AB 3334 4312 397F 49FF",
    ),
    (
        "Load word data immediate (alternate bases)",
        """
        lw r0, 0b1010
        lw r1, 0o123
        """,
        "300A 3153",
    ),
    (
        "Load word data immediate high-only",
        """
        lhi r0, 0
        lhi r1, 0x12
        lhi r2, 0xFF
        lhi r3, 0xAB00
        lhi r4, 0x3400
        lhi r5, 0xFF00
        """,
        "4000 4112 42FF 43AB 4434 45FF",
    ),
    (
        "decr",
        """
        decr r0
        decr r0, r0
        decr r5
        decr r6, r6
        decr r7, r8
        decr r15, r15
        """,
        "5800 5800 5855 5866 5887 58FF",
    ),
    (
        "incr",
        """
        incr r0
        incr r0, r0
        incr r5
        incr r6, r6
        incr r7, r8
        incr r15, r15
        """,
        "5900 5900 5955 5966 5987 59FF",
    ),
    (
        "not",
        """
        not r0
        not r0, r0
        not r5
        not r6, r6
        not r7, r8
        not r15, r15
        """,
        "5A00 5A00 5A55 5A66 5A87 5AFF",
    ),
    (
        "popcnt",
        """
        popcnt r0
        popcnt r0, r0
        popcnt r5
        popcnt r6, r6
        popcnt r7, r8
        popcnt r15, r15
        """,
        "5B00 5B00 5B55 5B66 5B87 5BFF",
    ),
    (
        "clz",
        """
        clz r0
        clz r0, r0
        clz r5
        clz r6, r6
        clz r7, r8
        clz r15, r15
        """,
        "5C00 5C00 5C55 5C66 5C87 5CFF",
    ),
    (
        "ctz",
        """
        ctz r0
        ctz r0, r0
        ctz r5
        ctz r6, r6
        ctz r7, r8
        ctz r15, r15
        """,
        "5D00 5D00 5D55 5D66 5D87 5DFF",
    ),
    (
        "rnd",
        """
        rnd r0
        rnd r0, r0
        rnd r5
        rnd r6, r6
        rnd r7, r8
        rnd r15, r15
        """,
        "5E00 5E00 5E55 5E66 5E87 5EFF",
    ),
    (
        "mov",
        # TODO: Should probably forbid single-arg mov?
        """
        mov r0
        mov r0, r0
        mov r5
        mov r6, r6
        mov r7, r8
        mov r15, r15
        """,
        "5F00 5F00 5F55 5F66 5F87 5FFF",
    ),
    (
        "nop single",
        """
        nop
        """,
        "5F00",
    ),
    (
        "nop multi",
        """
        nop
        nop
        nop
        """,
        "5F00 5F00 5F00",
    ),
    (
        "add",
        """
        add r0 r0
        add r3 r3
        add r7 r8
        add r15 r15
        """,
        "6000 6033 6078 60FF",
    ),
    (
        "add multi-space",
        """
        add r1    r2
        """,
        "6012",
    ),
    (
        "sub",
        """
        sub r0 r0
        sub r3 r3
        sub r7 r8
        sub r15 r15
        """,
        "6100 6133 6178 61FF",
    ),
    (
        "mul",
        """
        mul r0 r0
        mul r3 r3
        mul r7 r8
        mul r15 r15
        """,
        "6200 6233 6278 62FF",
    ),
    (
        "mulh",
        """
        mulh r0 r0
        mulh r3 r3
        mulh r7 r8
        mulh r15 r15
        """,
        "6300 6333 6378 63FF",
    ),
    (
        "divu",
        """
        divu r0 r0
        divu r3 r3
        divu r7 r8
        divu r15 r15
        """,
        "6400 6433 6478 64FF",
    ),
    (
        "divs",
        """
        divs r0 r0
        divs r3 r3
        divs r7 r8
        divs r15 r15
        """,
        "6500 6533 6578 65FF",
    ),
    (
        "modu",
        """
        modu r0 r0
        modu r3 r3
        modu r7 r8
        modu r15 r15
        """,
        "6600 6633 6678 66FF",
    ),
    (
        "mods",
        """
        mods r0 r0
        mods r3 r3
        mods r7 r8
        mods r15 r15
        """,
        "6700 6733 6778 67FF",
    ),
    (
        "and",
        """
        and r0 r0
        and r3 r3
        and r7 r8
        and r15 r15
        """,
        "6800 6833 6878 68FF",
    ),
    (
        "or",
        """
        or r0 r0
        or r3 r3
        or r7 r8
        or r15 r15
        """,
        "6900 6933 6978 69FF",
    ),
    (
        "xor",
        """
        xor r0 r0
        xor r3 r3
        xor r7 r8
        xor r15 r15
        """,
        "6A00 6A33 6A78 6AFF",
    ),
    (
        "sl",
        """
        sl r0 r0
        sl r3 r3
        sl r7 r8
        sl r15 r15
        """,
        "6B00 6B33 6B78 6BFF",
    ),
    (
        "srl",
        """
        srl r0 r0
        srl r3 r3
        srl r7 r8
        srl r15 r15
        """,
        "6C00 6C33 6C78 6CFF",
    ),
    (
        "sra",
        """
        sra r0 r0
        sra r3 r3
        sra r7 r8
        sra r15 r15
        """,
        "6D00 6D33 6D78 6DFF",
    ),
    (
        "gt",
        """
        gt r0 r0
        gt r15 r15
        gt r7 r8
        """,
        "8200 82FF 8278",
    ),
    (
        "eq",
        """
        eq r0 r0
        eq r15 r15
        eq r7 r8
        """,
        "8400 84FF 8478",
    ),
    (
        "ge",
        """
        ge r0 r0
        ge r15 r15
        ge r7 r8
        """,
        "8600 86FF 8678",
    ),
    (
        "lt",
        """
        lt r0 r0
        lt r15 r15
        lt r7 r8
        """,
        "8800 88FF 8878",
    ),
    (
        "ne",
        """
        ne r0 r0
        ne r15 r15
        ne r7 r8
        """,
        "8A00 8AFF 8A78",
    ),
    (
        "le",
        """
        le r0 r0
        le r15 r15
        le r7 r8
        """,
        "8C00 8CFF 8C78",
    ),
    (
        "gts",
        """
        gts r0 r0
        gts r15 r15
        gts r7 r8
        """,
        "8300 83FF 8378",
    ),
    (
        "ges",
        """
        ges r0 r0
        ges r15 r15
        ges r7 r8
        """,
        "8700 87FF 8778",
    ),
    (
        "lts",
        """
        lts r0 r0
        lts r15 r15
        lts r7 r8
        """,
        "8900 89FF 8978",
    ),
    (
        "les",
        """
        les r0 r0
        les r15 r15
        les r7 r8
        """,
        "8D00 8DFF 8D78",
    ),
    (
        "branch simple",
        """
        b r0 2
        b r1 8
        b r7 16
        b r8 +5
        b r15 +0x2
        b r7 -0x1
        """,
        "9000 9106 970E 9803 9F00 9780",
    ),
    (
        "branch extreme positive",
        """
        b r3 +0x7f
        b r4 127
        b r5 128
        b r6 129
        """,
        "937D 947D 957E 967F",
    ),
    (
        "branch extreme negative",
        """
        b r9 -127
        b r10 -128
        """,
        "99FE 9AFF",
    ),
]

NEGATIVE_TESTS = [
    (
        "garbage",
        """
        garbage
        """,
    ),
    (
        "return with arg",
        """
        ret 42
        """,
    ),
    (
        "late garbage",
        """
        ret
        garbage
        """,
    ),
    (
        "late return with arg",
        """
        ret
        ret 42
        """,
    ),
    (
        "CPUID with arg",
        """
        cpuid 42
        """,
    ),
    (
        "Debug-dump with arg",
        """
        debug 1337
        """,
    ),
    (
        "Time with arg",
        """
        time 0x42
        """,
    ),
    (
        "nop with arg imm",
        """
        nop 0x42
        """,
    ),
    (
        "nop with arg reg",
        """
        nop r5
        """,
    ),
    (
        "Store word no arg",
        """
        sw
        """,
    ),
    (
        "Store word one arg",
        """
        sw r4
        """,
    ),
    (
        "Store word no comma",
        """
        sw r4 r4
        """,
    ),
    (
        "Store word too many",
        """
        sw r4, r4, r4
        """,
    ),
    (
        "Store word illegal register",
        """
        sw r16, r1
        """,
    ),
    (
        "Store word other illegal register",
        """
        sw r4, r16
        """,
    ),
    (
        "Store word underscore register",
        """
        sw r1_3, r1
        """,
    ),
    (
        "Store word immediate address",
        """
        sw 0x1234, r1
        """,
    ),
    (
        "Store word immediate value",
        """
        sw r4, 0x1234
        """,
    ),
    (
        "Load word instruction immediate value",
        """
        lwi 0x1234, r4
        """,
    ),
    (
        "Load word instruction immediate address",
        # FIXME: This should be a feature!
        """
        lwi r5, 0x1234
        """,
    ),
    (
        "Load word data immediate value",
        """
        lw 0x1234, r5
        """,
    ),
    (
        "Load word data immediate (too low)",
        """
        lw r1, -0x8001
        """,
    ),
    (
        "Load word data immediate (too high)",
        """
        lw r0, 65536
        """,
    ),
    (
        "Load word data immediate (garbage)",
        """
        lw r0, garbage
        """,
    ),
    (
        "Load word data immediate high-only from register",
        """
        lhi r0, r1
        """,
    ),
    (
        "Load word data immediate high-only invalid",
        """
        lhi r0, 0x1234
        """,
    ),
    (
        "decr no args",
        """
        decr
        """,
    ),
    (
        "decr too many args",
        """
        decr r1, r2, r3
        """,
    ),
    (
        "decr 1-arg, imm",
        """
        decr 0x123
        """,
    ),
    (
        "decr 2-arg, imm reg",
        """
        decr 123, r0
        """,
    ),
    (
        "decr 2-arg, reg imm",
        """
        decr r0, 123
        """,
    ),
    (
        "incr no args",
        """
        incr
        """,
    ),
    (
        "not no args",
        """
        not
        """,
    ),
    (
        "clz no args",
        """
        clz
        """,
    ),
    (
        "ctz no args",
        """
        ctz
        """,
    ),
    (
        "rnd no args",
        """
        rnd
        """,
    ),
    (
        "mov no args",
        """
        mov
        """,
    ),
    (
        "popcnt no args",
        """
        popcnt
        """,
    ),
    (
        "add comma space",
        """
        add r4, r5
        """,
    ),
    (
        "add comma nospace",
        """
        add r4,r5
        """,
    ),
    (
        "add three args",
        """
        add r4 r5 r6
        """,
    ),
    (
        "add noargs",
        """
        add
        """,
    ),
    (
        "add space comma space",
        """
        add r4 , r5
        """,
    ),
    (
        "sub noargs",
        """
        sub
        """,
    ),
    (
        "mul noargs",
        """
        mul
        """,
    ),
    (
        "mulh noargs",
        """
        mulh
        """,
    ),
    (
        "divu noargs",
        """
        divu
        """,
    ),
    (
        "divs noargs",
        """
        divs
        """,
    ),
    (
        "modu noargs",
        """
        modu
        """,
    ),
    (
        "mods noargs",
        """
        mods
        """,
    ),
    (
        "and noargs",
        """
        and
        """,
    ),
    (
        "or noargs",
        """
        or
        """,
    ),
    (
        "xor noargs",
        """
        xor
        """,
    ),
    (
        "sl noargs",
        """
        sl
        """,
    ),
    (
        "srl noargs",
        """
        srl
        """,
    ),
    (
        "sra noargs",
        """
        sra
        """,
    ),
    (
        "lt noargs",
        """
        lt
        """,
    ),
    # Skip the other compare instructions, there's not much to test anyway.
    (
        "branch comma",
        """
        b r5, 5
        """,
    ),
    (
        "branch too large",
        """
        b r5 130
        """,
    ),
    (
        "branch too negative",
        """
        b r10 -129
        """,
    ),
    (
        "branch single arg",
        """
        b r10
        """,
    ),
    (
        "branch to reg",
        """
        b r10 r5
        """,
    ),
    (
        "branch by 0",
        """
        b r10 0
        """,
    ),
    (
        "branch by 1",
        """
        b r10 1
        """,
    ),
]


class AsmTests(unittest.TestCase):
    def test_empty(self):
        asm.ERROR_OUTPUT = False
        self.assertEqual(b"\x00" * asm.SEGMENT_LENGTH, asm.compile_to_segment(""))
        self.assertEqual(b"\x00" * asm.SEGMENT_LENGTH, asm.compile_to_segment("\n"))

    def test_testsuite_names(self):
        nameCounter = Counter(name for name, _, _ in ASM_TESTS)
        for name, count in nameCounter.items():
            with self.subTest(t="ASM_TESTS", name=name):
                self.assertEqual(count, 1)
        nameCounter = Counter(name for name, _ in NEGATIVE_TESTS)
        for name, count in nameCounter.items():
            with self.subTest(t="NEGATIVE_TESTS", name=name):
                self.assertEqual(count, 1)

    def test_hardcoded(self):
        asm.ERROR_OUTPUT = False
        for i, (name, asm_text, code_prefix_hex) in enumerate(ASM_TESTS):
            with self.subTest(i=i, name=name):
                expected_segment = bytearray.fromhex(code_prefix_hex)
                self.assertTrue(len(expected_segment) <= asm.SEGMENT_LENGTH)
                self.assertEqual(len(expected_segment) % 2, 0)
                padding = b"\x00" * (asm.SEGMENT_LENGTH - len(expected_segment))
                expected_segment.extend(padding)
                self.assertEqual(expected_segment, asm.compile_to_segment(asm_text))

    def test_negative(self):
        asm.ERROR_OUTPUT = False
        for i, (name, asm_text) in enumerate(NEGATIVE_TESTS):
            with self.subTest(i=i, name=name):
                self.assertIsNone(asm.compile_to_segment(asm_text))


if __name__ == "__main__":
    unittest.main()
