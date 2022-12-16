#!/usr/bin/env python3

from collections import Counter
import asm
import unittest


class ModTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(0, asm.mod_s16(0))

    def test_identity(self):
        identities = [1, -1, 2, -2, 0x1234, 0x7FFE, 0x7FFF, -0x1234, -0x7FFF, -0x8000]
        for i, value in enumerate(identities):
            with self.subTest(i=i):
                self.assertEqual(value, asm.mod_s16(value))

    def test_wrapping(self):
        pairs = [
            (0x8000, -0x8000),
            (0x8001, -0x7FFF),
            (0x8002, -0x7FFE),
            (0xFFFE, -2),
            (0xFFFF, -1),
            (0x10000, 0),
            (-0x8001, 0x7FFF),
            (-0x8002, 0x7FFE),
            (-0xFFFF, 1),
            (-0x10000, 0),
        ]
        for given, expected in pairs:
            with self.subTest(given=given):
                self.assertEqual(expected, asm.mod_s16(given))


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
        "Load word data immediate (single insn, extreme)",
        """
        lw r7, 0xFFFF
        lw r11, -42
        lw r12, -128
        """,
        "37FF 3BD6 3C80",
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
        """
        mov r0, r1
        mov r6, r2
        mov r7, r8
        mov r15, r14
        """,
        "5F10 5F26 5F87 5FEF",
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
    (
        "jump by immediate simple",
        """
        j +5
        j +2
        j -1
        j -42
        """,
        "A003 A000 A800 A829",
    ),
    (
        "jump by immediate extreme positive",
        """
        j 123
        j 0x123
        j 0x7FE
        j 0x7FF
        j 0x800
        j 0x801
        """,
        "A079 A121 A7FC A7FD A7FE A7FF",
    ),
    (
        "jump by immediate extreme negative",
        """
        j -123
        j -0x123
        j -0x7FE
        j -0x7FF
        j -0x800
        """,
        "A87A A922 AFFD AFFE AFFF",
    ),
    (
        "jump to register onearg",
        """
        j r0
        j r1
        j r15
        """,
        "B000 B100 BF00",
    ),
    (
        "jump to register twoarg positive",
        """
        j r0 +0
        j r1 1
        j r2 0x12
        j r3 +127
        """,
        "B000 B101 B212 B37F",
    ),
    (
        "jump to register twoarg negative",
        """
        j r4 -0
        j r5 -1
        j r6 -0x12
        """,
        "B400 B5FF B6EE",
    ),
    (
        "jump to register twoarg negative extreme",
        """
        j r7 -127
        j r8 -128
        """,
        "B781 B880",
    ),
    (
        "offset empty",
        """
        .offset 0x1234
        """,
        "0000",
    ),
    (
        "offset basic",
        """
        .offset 0x1234
        ret
        """,
        "0000 " * 0x1234 + "102A",
    ),
    (
        "offset low",
        """
        lw r1, 0x23
        .offset 3
        ret
        """,
        "3123 0000 0000 102A",
    ),
    (
        "offset weird order",
        """
        .offset 3
        ret
        .offset 0
        lw r1, 0x23
        """,
        "3123 0000 0000 102A",
    ),
    (
        "offset extreme",
        """
        .offset +0xFFFF
        lw r1, 0x23
        lw r4, 0x56
        """,
        "3456" + (" 0000" * (0x1_0000 - 2)) + " 3123",
    ),
    (
        "literal simple",
        """
        .word 0xABCD
        .word 1234
        .word 0
        .word -9
        """,
        "ABCD 04D2 0000 FFF7",
    ),
    (
        "literal extreme",
        """
        .word 0xFFFF
        .word -0x8000
        .word -0x7FFF
        """,
        "FFFF 8000 8001",
    ),
    (
        "label simple",
        """
        .label _hello_world
        ret
        """,
        "102A",
    ),
    (
        "label multi",
        """
        .label _hello_world
        .label _hello_world_again
        ret
        .label _hello_more_world
        lw r4, 0x56
        """,
        "102A 3456",
    ),
    (
        "branch label low negative",
        """
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        b r4 _some_label
        """,
        "3210 3333 9480",
    ),
    (
        "branch label medium negative",
        """
        .label _some_label
        lw r3, 0x33
        lw r4, 0x44
        lw r5, 0x55
        b r4 _some_label
        """,
        "3333 3444 3555 9482",
    ),
    (
        "branch label barely-overflow negative",
        """
        ret
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFF
        b r4 _some_label
        """,
        "102A 3333" + (" 0000" * (65536 - 3)) + " 9400",
    ),
    (
        "branch label overflow negative",
        """
        ret
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFE
        b r4 _some_label
        lw r5, 0x79
        """,
        "102A 3333" + (" 0000" * (65536 - 4)) + " 9401 3579",
    ),
    (
        "branch label extreme negative",
        """
        ret
        .label _some_label
        lw r3, 0x33
        .offset 0x0081
        b r4 _some_label # the label is at relative -0x80
        """,
        "102A 3333" + (" 0000" * (0x81 - 2)) + " 94FF",
    ),
    (
        "branch label negative to undef",
        """
        ret
        .label _some_label
        .offset 0x005
        b r4 _some_label # the label is at relative -4
        """,
        "102A 0000 0000 0000 0000 9483",
    ),
    (
        "branch label low positive",
        """
        b r6 _some_label
        lw r2, 0x22
        .label _some_label
        lw r3, 0x33
        """,
        "9600 3222 3333",
    ),
    (
        "branch label medium positive",
        """
        lw r3, 0x33
        b r7 _some_label
        lw r4, 0x44
        lw r5, 0x55
        lw r6, 0x66
        .label _some_label
        lw r7, 0x77
        """,
        "3333 9702 3444 3555 3666 3777",
    ),
    (
        "branch label barely-overflow positive",
        """
        b r4 _some_label
        ret
        .offset 0xFFFF
        .label _some_label
        lw r3, 0x33
        """,
        "9480 102A" + (" 0000" * (65536 - 3)) + " 3333",
    ),
    (
        "branch label overflow positive",
        """
        lw r3, 0x33
        lw r4, 0x56
        b r4 _some_label # offset is -4
        ret
        .offset 0xFFFE
        .label _some_label
        lw r6, 0x66
        lw r2, 0x10
        """,
        "3333 3456 9483 102A" + (" 0000" * (65536 - 6)) + " 3666 3210",
    ),
    (
        "branch label extreme positive",
        """
        lw r3, 0x33
        b r4 _some_label # the label is at relative +0x81
        lw r4, 0x56
        .offset 0x0082
        .label _some_label
        nop
        """,
        "3333 947F 3456" + (" 0000" * (0x82 - 3)) + " 5F00",
    ),
    (
        "branch label positive to undef",
        """
        b r4 _some_label
        ret
        .offset 5
        .label _some_label
        """,
        "9403 102A",
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
    (
        "jump noarg",
        """
        j
        """,
    ),
    (
        "jump two arg immediate, comma",
        """
        j 0x12, 0x34
        """,
    ),
    (
        "jump two arg immediate, space",
        """
        j 0x12 0x34
        """,
    ),
    (
        "jump by immediate extreme positive",
        """
        j 0x802
        """,
    ),
    (
        "jump by immediate extreme negative",
        """
        j -0x801
        """,
    ),
    (
        "jump to register onearg",
        """
        j r16
        """,
    ),
    (
        "jump to register twoarg extreme positive",
        """
        j r3 +128
        """,
    ),
    (
        "jump to register twoarg extreme negative",
        """
        j r8 -129
        """,
    ),
    (
        "offset negative",
        """
        .offset -1
        """,
    ),
    (
        "offset overwrite",
        """
        ret
        .offset 0
        ret
        """,
    ),
    (
        "offset overwrite indirect",
        """
        .offset 2
        ret
        .offset 0
        ret
        ret
        ret # Bam!
        """,
    ),
    (
        "literal too positive",
        """
        .word 65536
        """,
    ),
    (
        "literal too negative decimal",
        """
        .word -32769
        """,
    ),
    (
        "literal too negative hex",
        """
        .word -0x8001
        """,
    ),
    (
        "mov single-arg",
        """
        mov r0
        """,
    ),
    (
        "mov noop",
        """
        mov r1, r1
        """,
    ),
    (
        "overwrite zeros",
        """
        .word 0x0000
        .offset 0
        .word 0x0000
        """,
    ),
    (
        "label no name",
        """
        .label
        """,
    ),
    (
        "label bad name",
        """
        .label 1234
        """,
    ),
    (
        "label no underscore",
        """
        .label foobar
        """,
    ),
    (
        "label too short",
        """
        .label _
        """,
    ),
    (
        "label multidef",
        """
        .label _hello_world
        ret
        .label _hello_world
        """,
    ),
    (
        "label special $",
        """
        .label _$hello_world
        """,
    ),
    (
        "label special %",
        """
        .label _%hello_world
        """,
    ),
    (
        "label special &",
        """
        .label _&hello_world
        """,
    ),
    (
        "label special (",
        """
        .label _(hello_world
        """,
    ),
    (
        "label special )",
        """
        .label _)hello_world
        """,
    ),
    (
        "label special =",
        """
        .label _=hello_world
        """,
    ),
    (
        "label special single quote",
        """
        .label _'hello_world
        """,
    ),
    (
        "label special double quote",
        """
        .label _"hello_world
        """,
    ),
    (
        "label special [",
        """
        .label _[hello_world
        """,
    ),
    (
        "label special ]",
        """
        .label _]hello_world
        """,
    ),
    (
        "branch unknown label",
        """
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        b r4 _wrong_label
        """,
    ),
    (
        "branch label zero",
        """
        lw r2, 0x10
        .label _some_label
        b r4 _some_label
        """,
    ),
    (
        "branch label one",
        """
        lw r2, 0x10
        b r4 _some_label
        .label _some_label
        lw r2, 0x10
        """,
    ),
    (
        "branch label one overflow",
        """
        .label _some_label
        lw r2, 0x10
        .offset 0xFFFF
        b r4 _some_label
        """,
    ),
    (
        "branch label too extreme negative",
        """
        ret
        .label _some_label
        lw r3, 0x33
        .offset 0x0082
        b r4 _some_label # the label is at relative -0x81
        """,
    ),
    (
        "branch label too extreme positive",
        """
        lw r3, 0x33
        b r4 _some_label # the label is at relative +0x82
        lw r4, 0x56
        .offset 0x0083
        .label _some_label
        nop
        """,
    ),
]

TESTS_INSTRUCTIONS_RS = [
    (
        "from test_time_jump",
        """
        j r0 +0x0005
        nop
        nop
        nop
        nop
        time
        """,
        "B005 5F00 5F00 5F00 5F00 102D",
    ),
    (
        "from test_time_long",
        """
        lw r7, 0xFFAB
        decr r7
        b r7 -0x1
        time
        ret
        """,
        "37AB 5877 9780 102D 102A",
    ),
    # FIXME: Labels not implemented yet
    # (
    #     "from test_time_very_long",
    #     """
    #     lw r7, 0xB505 # executed 1 time
    #     mv r1, r7 # executed 1 time
    #     .label outer_loop
    #     mv r2, r7 # executed 0xB505 times
    #     .label inner_loop
    #     decr r2 # executed 0xB505 * 0xB505 times
    #     b r2 inner_loop # (offset is -0x1) # executed 0xB505 * 0xB505 times
    #     decr r1 # executed 0xB505 times
    #     b r1 outer_loop # (offset is -0x4) # executed 0xB505 times
    #     time # executed 0 times or 1 time, depending on how you look at it
    #     ret # executed 0 times
    #     # Total steps: (3 or 4) + 3 * 0xB505 + 2 * 0xB505 * 0xB505 = 0x100024344 or 0x100024345
    #     """,
    #     "3705 47B5 5F71 5F72 5822 9280 5811 9183 102D 102A",
    # ),
    (
        "from test_store_data_doc",
        """
        lw r2, 0x1234
        lw r5, 0x5678
        sw r2, r5
        """,
        "3234 4212 3578 4556 2025",
    ),
    (
        "from test_store_data_simple",
        """
        lw r2, 0x0045
        lw r5, 0x0067
        sw r2, r5
        """,
        "3245 3567 2025",
    ),
    (
        "from test_load_data_doc",
        """
        lw r2, 0x1234
        lw r5, r2
        """,
        "3234 4212 2125",
    ),
    (
        "from test_load_data_simple",
        """
        lw r2, 0x0005
        lw r5, r2
        """,
        "3205 2125",
    ),
    (
        "from test_load_instruction_doc",
        """
        lw r2, 0x1234
        lwi r5, r2
        """,
        "3234 4212 2225",
    ),
    (
        "from test_load_instruction_simple",
        """
        lw r2, 0x0005
        lwi r5, r2
        """,
        "3205 2225",
    ),
    (
        "from test_load_imm_high_doc_setup",
        """
        lw r10, 0x1234
        """,
        "3A34 4A12",
    ),
    (
        "from test_load_imm_high_doc",
        """
        lw r10, 0x1234
        lhi r10, 0x5600
        """,
        "3A34 4A12 4A56",
    ),
    (
        "from test_load_imm_high_simple",
        """
        lhi r5, 0xAB00
        """,
        "45AB",
    ),
    (
        "from test_jump_register_doc1",
        """
        lhi r7, 0x1200
        j r7 +0x0034
        """,
        "4712 B734",
    ),
    (
        "from test_jump_register_doc2",
        """
        lw r7, 0x1234
        j r7 -0x0001
        """,
        "3734 4712 B7FF",
    ),
    (
        "from test_jump_register_simple",
        """
        j r0 +0x0042
        """,
        "B042",
    ),
    (
        "from test_jump_register_overflow",
        """
        lw r7, 0xFFFF
        j r7 +0x0010
        """,
        "37FF B710",
    ),
    (
        "from test_jump_register_underflow",
        """
        j r0 -0x0080
        """,
        "B080",
    ),
    (
        "from test_jump_register_extreme_positive_imm",
        """
        j r0 +0x7F
        """,
        "B07F",
    ),
    (
        "from test_jump_register_extreme_negative_imm",
        """
        j r0 -0x80
        """,
        "B080",
    ),
    (
        "from test_jump_register_extreme_positive",
        """
        lw r7, 0xFFFF
        j r7 +0x7F
        """,
        "37FF B77F",
    ),
    (
        "from test_jump_register_extreme_positive_nowrap",
        """
        lw r7, 0x7FFF
        j r7 +0x7F
        """,
        "37FF 477F B77F",
    ),
    (
        "from test_jump_register_extreme_negative",
        """
        lw r7, 0xFFFF
        j r7 -0x80
        """,
        "37FF B780",
    ),
    (
        "from test_jump_register_extreme_negative_signedish",
        """
        lw r7, 0x8000
        j r7 -0x80
        """,
        # The example doesn't use 3700, but the assembler shouldn't make such optimizations.
        "3700 4780 B780",
    ),
    (
        "from test_program_counter_wraps",
        """
        lw r7, 0xFFFF
        j r7 +0x0000
        .offset 0xFFFF
        lw r4, 0x0012
        """,
        "37FF B700 " + ("0000 " * (65536 - 3)) + "3412",
    ),
    (
        "from test_jump_imm_doc1",
        """
        lhi r3, 0x5000
        j r3 +0x0000
        .offset 0x5000
        j +0x125
        """,
        "4350 B300 " + ("0000 " * (0x5000 - 2)) + "A123",
    ),
    (
        "from test_jump_imm_doc2",
        """
        lhi r3, 0x1200
        j r3 +0x0034
        .offset 0x1234
        j -0x1
        """,
        "4312 B334 " + ("0000 " * (0x1234 - 2)) + "A800",
    ),
    (
        "from test_jump_immediate_overflow",
        """
        lw r3, 0xFF00
        j r3 +0x0000
        .offset 0xFF00
        j +0x202
        """,
        # The example doesn't use 3300, but the assembler shouldn't make such optimizations.
        "3300 43FF B300 " + ("0000 " * (0xFF00 - 3)) + "A200" + (" 0000" * 0xFF),
    ),
    (
        "from test_jump_immediate_underflow",
        """
        j -0x031
        """,
        "A830",
    ),
    (
        "from test_jump_immediate_extreme_positive",
        """
        j +0x801
        """,
        "A7FF",
    ),
    (
        "from test_jump_immediate_extreme_negative",
        """
        j -0x800
        """,
        "AFFF",
    ),
    (
        "from test_branch_doc1",
        """
        lw r3, 0x0001
        lhi r7, 0x1200
        j r7 +0x0034
        .offset 0x1234
        b r3 -0x1
        """,
        "3301 4712 B734 " + ("0000 " * (0x1234 - 3)) + "9380",
    ),
    (
        "from test_branch_doc2",
        """
        b r5 -0x1
        """,
        "9580",
    ),
    (
        "from test_compare_doc",
        """
        lw r3, 0x0005
        lw r4, 0x0007
        ne r3 r4
        """,
        "3305 3407 8A34",
    ),
    (
        "from test_unary_doc1",
        """
        lw r5, 0x1234
        not r6, r5
        """,
        "3534 4512 5A56",
    ),
    (
        "from test_unary_doc2",
        """
        lw r3, 41
        incr r3
        """,
        "3329 5933",
    ),
    (
        "from test_unary_rnd_inclusive",
        """
        lw r1, 5
        rnd r2, r1
        le r2 r1
        ge r2 r0
        """,
        "3105 5E12 8C21 8620",
    ),
    (
        "from test_unary_rnd_extreme",
        """
        lw r1, 0xFFFF
        rnd r2, r1
        eq r2 r1
        eq r2 r0
        """,
        "31FF 5E12 8421 8420",
    ),
    (
        "from test_binary_doc",
        """
        lw r5, 5
        lw r6, 7
        mul r5 r6
        """,
        "3505 3607 6256",
    ),
    # FIXME: labels not yet implemented
    # (
    #     "from test_fibonacci",
    #     """
    #     lw r0, 24
    #     lw r1, 1
    #     .label start
    #     add r1 r2
    #     decr r0
    #     sw r0, r2
    #     add r2 r1
    #     decr r0
    #     sw r0, r1
    #     b r0 start # (offset is -0x6)
    #     ret
    #     """,
    #     "3018 3101 6012 5800 2002 6021 5800 2001 9085 102A",
    # ),
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
                if len(expected_segment) > asm.SEGMENT_LENGTH // 2:
                    # If a very long sequence is specified, it's probably supposed to be the entire program.
                    self.assertEqual(len(expected_segment), asm.SEGMENT_LENGTH)
                self.assertEqual(len(expected_segment) % 2, 0)
                padding = b"\x00" * (asm.SEGMENT_LENGTH - len(expected_segment))
                expected_segment.extend(padding)
                self.assertEqual(expected_segment, asm.compile_to_segment(asm_text))

    def test_negative(self):
        asm.ERROR_OUTPUT = False
        for i, (name, asm_text) in enumerate(NEGATIVE_TESTS):
            with self.subTest(i=i, name=name):
                self.assertIsNone(asm.compile_to_segment(asm_text))

    def test_from_instructions_rs(self):
        asm.ERROR_OUTPUT = False
        for i, (name, asm_text, code_prefix_hex) in enumerate(TESTS_INSTRUCTIONS_RS):
            with self.subTest(i=i, name=name):
                expected_segment = bytearray.fromhex(code_prefix_hex)
                self.assertTrue(len(expected_segment) <= asm.SEGMENT_LENGTH)
                if len(expected_segment) > asm.SEGMENT_LENGTH // 2:
                    # If a very long sequence is specified, it's probably supposed to be the entire program.
                    self.assertEqual(len(expected_segment), asm.SEGMENT_LENGTH)
                self.assertEqual(len(expected_segment) % 2, 0)
                padding = b"\x00" * (asm.SEGMENT_LENGTH - len(expected_segment))
                expected_segment.extend(padding)
                self.assertEqual(expected_segment, asm.compile_to_segment(asm_text))


if __name__ == "__main__":
    unittest.main()
