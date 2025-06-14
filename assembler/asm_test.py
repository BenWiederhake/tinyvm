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
    ("empty", "", "", [], dict()),
    (
        "newline",
        # No trailing backslash here!
        """
        """,
        "",
        [],
        dict(),
    ),
    (
        "comment",
        """\
        # Hello, world!
        """,
        "",
        [],
        dict(),
    ),
    (
        "yield",
        """\
        yield
        """,
        "102A",
        [],
        {0: 1},
    ),
    (
        "inline comment",
        """\
        # This is awesome.
        yield  # Yield, yo!
        # Hooray!
        """,
        "102A",
        [],
        {0: 2},
    ),
    (
        "inline comment multi",
        """\
        yield # Yield   # but you knew that already, didn't you?
        """,
        "102A",
        [],
        {0: 1},
    ),
    (
        "illegal",
        """\
        ill
        """,
        "FFFF",
        [],
        {0: 1},
    ),
    (
        "more than one instruction",
        """\
        yield
        ill
        """,
        "102A FFFF",
        [],
        {0: 1, 1: 2},
    ),
    (
        "CPUID",
        """\
        cpuid
        """,
        "102B",
        [],
        {0: 1},
    ),
    (
        "Debug-dump",
        """\
        debug
        """,
        "102C",
        [],
        {0: 1},
    ),
    (
        "Time",
        """\
        time
        """,
        "102D",
        [],
        {0: 1},
    ),
    (
        "Store word",
        """\
        sw r0, r0
        sw r1, r0
        sw r10, r15
        """,
        "2000 2010 20AF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "Load word instruction",
        """\
        lwi r0, r0
        lwi r0, r1
        lwi r15, r10
        """,
        "2200 2210 22AF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "Load word data, memory-only",
        """\
        lw r0, r0
        lw r0, r1
        lw r15, r10
        """,
        "2100 2110 21AF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "Load word data immediate (single insn)",
        """\
        lw r0, 0x0000
        lw r1, -1
        lw r5, 42
        lw r8, 0x7F
        lw r9, 0xFF80
        lw r10, 0xFFFE
        """,
        "3000 31FF 352A 387F 3980 3AFE",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "Load word data immediate (single insn, extreme)",
        """\
        lw r7, 0xFFFF
        lw r11, -42
        lw r12, -128
        """,
        "37FF 3BD6 3C80",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "Load word data immediate (double insn)",
        """\
        lw r0, 0x0081
        lw r1, -0x81
        lw r2, 0xABCD
        lw r3, 0x1234
        lw r9, 0xFF7F
        """,
        "3081 4000 317F 41FF 32CD 42AB 3334 4312 397F 49FF",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 5, 9: 5},
    ),
    (
        "Load word data immediate (alternate bases)",
        """\
        lw r0, 0b1010
        lw r1, 0o123
        """,
        "300A 3153",
        [],
        {0: 1, 1: 2},
    ),
    (
        "Load word data immediate high-only",
        """\
        lhi r0, 0
        lhi r1, 0x12
        lhi r2, 0xFF
        lhi r3, 0xAB00
        lhi r4, 0x3400
        lhi r5, 0xFF00
        """,
        "4000 4112 42FF 43AB 4434 45FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "decr",
        """\
        decr r0
        decr r0, r0
        decr r5
        decr r6, r6
        decr r7, r8
        decr r15, r15
        """,
        "5800 5800 5855 5866 5887 58FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "incr",
        """\
        incr r0
        incr r0, r0
        incr r5
        incr r6, r6
        incr r7, r8
        incr r15, r15
        """,
        "5900 5900 5955 5966 5987 59FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "not",
        """\
        not r0
        not r0, r0
        not r5
        not r6, r6
        not r7, r8
        not r15, r15
        """,
        "5A00 5A00 5A55 5A66 5A87 5AFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "popcnt",
        """\
        popcnt r0
        popcnt r0, r0
        popcnt r5
        popcnt r6, r6
        popcnt r7, r8
        popcnt r15, r15
        """,
        "5B00 5B00 5B55 5B66 5B87 5BFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "clz",
        """\
        clz r0
        clz r0, r0
        clz r5
        clz r6, r6
        clz r7, r8
        clz r15, r15
        """,
        "5C00 5C00 5C55 5C66 5C87 5CFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "ctz",
        """\
        ctz r0
        ctz r0, r0
        ctz r5
        ctz r6, r6
        ctz r7, r8
        ctz r15, r15
        """,
        "5D00 5D00 5D55 5D66 5D87 5DFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "rnd",
        """\
        rnd r0
        rnd r0, r0
        rnd r5
        rnd r6, r6
        rnd r7, r8
        rnd r15, r15
        """,
        "5E00 5E00 5E55 5E66 5E87 5EFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "mov",
        """\
        mov r0, r1
        mov r6, r2
        mov r7, r8
        mov r15, r14
        """,
        "5F10 5F26 5F87 5FEF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "nop single",
        """\
        nop
        """,
        "5F00",
        [],
        {0: 1},
    ),
    (
        "nop multi",
        """\
        nop
        nop
        nop
        """,
        "5F00 5F00 5F00",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "add",
        """\
        add r0 r0
        add r3 r3
        add r7 r8
        add r15 r15
        """,
        "6000 6033 6078 60FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "add multi-space",
        """\
        add r1    r2
        """,
        "6012",
        [],
        {0: 1},
    ),
    (
        "sub",
        """\
        sub r0 r0
        sub r3 r3
        sub r7 r8
        sub r15 r15
        """,
        "6100 6133 6178 61FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "mul",
        """\
        mul r0 r0
        mul r3 r3
        mul r7 r8
        mul r15 r15
        """,
        "6200 6233 6278 62FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "mulh",
        """\
        mulh r0 r0
        mulh r3 r3
        mulh r7 r8
        mulh r15 r15
        """,
        "6300 6333 6378 63FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "divu",
        """\
        divu r0 r0
        divu r3 r3
        divu r7 r8
        divu r15 r15
        """,
        "6400 6433 6478 64FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "divs",
        """\
        divs r0 r0
        divs r3 r3
        divs r7 r8
        divs r15 r15
        """,
        "6500 6533 6578 65FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "modu",
        """\
        modu r0 r0
        modu r3 r3
        modu r7 r8
        modu r15 r15
        """,
        "6600 6633 6678 66FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "mods",
        """\
        mods r0 r0
        mods r3 r3
        mods r7 r8
        mods r15 r15
        """,
        "6700 6733 6778 67FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "and",
        """\
        and r0 r0
        and r3 r3
        and r7 r8
        and r15 r15
        """,
        "6800 6833 6878 68FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "or",
        """\
        or r0 r0
        or r3 r3
        or r7 r8
        or r15 r15
        """,
        "6900 6933 6978 69FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "xor",
        """\
        xor r0 r0
        xor r3 r3
        xor r7 r8
        xor r15 r15
        """,
        "6A00 6A33 6A78 6AFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "sl",
        """\
        sl r0 r0
        sl r3 r3
        sl r7 r8
        sl r15 r15
        """,
        "6B00 6B33 6B78 6BFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "srl",
        """\
        srl r0 r0
        srl r3 r3
        srl r7 r8
        srl r15 r15
        """,
        "6C00 6C33 6C78 6CFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "sra",
        """\
        sra r0 r0
        sra r3 r3
        sra r7 r8
        sra r15 r15
        """,
        "6D00 6D33 6D78 6DFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "gt",
        """\
        gt r0 r1
        gt r14 r15
        gt r7 r8
        """,
        "8201 82EF 8278",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "eq",
        """\
        eq r0 r1
        eq r14 r15
        eq r7 r8
        """,
        "8401 84EF 8478",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "ge",
        """\
        ge r0 r1
        ge r14 r15
        ge r7 r8
        """,
        "8601 86EF 8678",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "lt",
        """\
        lt r0 r1
        lt r14 r15
        lt r7 r8
        """,
        "8801 88EF 8878",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "ne",
        """\
        ne r0 r1
        ne r14 r15
        ne r7 r8
        """,
        "8A01 8AEF 8A78",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "le",
        """\
        le r0 r1
        le r14 r15
        le r7 r8
        """,
        "8C01 8CEF 8C78",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "gts",
        """\
        gts r0 r1
        gts r14 r15
        gts r7 r8
        """,
        "8301 83EF 8378",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "ges",
        """\
        ges r0 r1
        ges r14 r15
        ges r7 r8
        """,
        "8701 87EF 8778",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "lts",
        """\
        lts r0 r1
        lts r14 r15
        lts r7 r8
        """,
        "8901 89EF 8978",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "les",
        """\
        les r0 r1
        les r14 r15
        les r7 r8
        """,
        "8D01 8DEF 8D78",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "branch simple",
        """\
        b r0 2
        b r1 8
        b r7 16
        b r8 +5
        b r15 +0x2
        b r7 -0x1
        """,
        "9000 9106 970E 9803 9F00 9780",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "branch extreme positive",
        """\
        b r3 +0x7f
        b r4 127
        b r5 128
        b r6 129
        """,
        "937D 947D 957E 967F",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "branch extreme negative",
        """\
        b r9 -127
        b r10 -128
        """,
        "99FE 9AFF",
        [],
        {0: 1, 1: 2},
    ),
    (
        "jump by immediate simple",
        """\
        j +5
        j +2
        j -1
        j -42
        """,
        "A003 A000 A800 A829",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "jump by immediate extreme positive",
        """\
        j 123
        j 0x123
        j 0x7FE
        j 0x7FF
        j 0x800
        j 0x801
        """,
        "A079 A121 A7FC A7FD A7FE A7FF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "jump by immediate extreme negative",
        """\
        j -123
        j -0x123
        j -0x7FE
        j -0x7FF
        j -0x800
        """,
        "A87A A922 AFFD AFFE AFFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5},
    ),
    (
        "jump to register onearg",
        """\
        j r0
        j r1
        j r15
        """,
        "B000 B100 BF00",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "jump to register twoarg positive",
        """\
        j r0 +0
        j r1 1
        j r2 0x12
        j r3 +127
        """,
        "B000 B101 B212 B37F",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "jump to register twoarg negative",
        """\
        j r4 -0
        j r5 -1
        j r6 -0x12
        """,
        "B400 B5FF B6EE",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "jump to register twoarg negative extreme",
        """\
        j r7 -127
        j r8 -128
        """,
        "B781 B880",
        [],
        {0: 1, 1: 2},
    ),
    (
        "offset empty",
        """\
        .offset 0x1234
        """,
        "0000",
        [],
        dict(),
    ),
    (
        "offset basic",
        """\
        .offset 0x1234
        yield
        """,
        "0000 " * 0x1234 + "102A",
        [],
        {0x1234: 2},
    ),
    (
        "offset low",
        """\
        lw r1, 0x23
        .offset 3
        yield
        """,
        "3123 0000 0000 102A",
        [],
        {0: 1, 3: 3},
    ),
    (
        "offset weird order",
        """\
        .offset 3
        yield
        .offset 0
        lw r1, 0x23
        """,
        "3123 0000 0000 102A",
        [],
        {0: 4, 3: 2},
    ),
    (
        "offset extreme",
        """\
        .offset +0xFFFF
        lw r1, 0x23
        lw r4, 0x56
        """,
        "3456" + (" 0000" * (0x1_0000 - 2)) + " 3123",
        ["line 2: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 3, 0xFFFF: 2},
    ),
    (
        "literal simple",
        """\
        .word 0xABCD
        .word 1234
        .word 0
        .word -9
        """,
        "ABCD 04D2 0000 FFF7",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "literal extreme",
        """\
        .word 0xFFFF
        .word -0x8000
        .word -0x7FFF
        """,
        "FFFF 8000 8001",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "label simple",
        """\
        .label _hello_world
        yield
        # Cannot have an unreferenced label, sadly :(
        .offset _hello_world
        """,
        "102A",
        [],
        {0: 2},
    ),
    (
        "label multi",
        """\
        .label _hello_world
        .label _hello_world_again
        yield
        .label _hello_more_world
        lw r4, 0x56
        # Cannot have an unreferenced label, sadly :(
        .offset _hello_world
        .offset _hello_world_again
        .offset _hello_more_world
        """,
        "102A 3456",
        [],
        {0: 3, 1: 5},
    ),
    (
        "branch label low negative",
        """\
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        b r4 _some_label
        """,
        "3210 3333 9480",
        [],
        {0: 1, 1: 3, 2: 4},
    ),
    (
        "branch label medium negative",
        """\
        .label _some_label
        lw r3, 0x33
        lw r4, 0x44
        lw r5, 0x55
        b r4 _some_label
        """,
        "3333 3444 3555 9482",
        [],
        {0: 2, 1: 3, 2: 4, 3: 5},
    ),
    (
        "branch label barely-overflow negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFF
        b r4 _some_label
        """,
        "102A 3333" + (" 0000" * (65536 - 3)) + " 9400",
        ["line 5: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 3, 0xFFFF: 5},
    ),
    (
        "branch label overflow negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFE
        b r4 _some_label
        lw r5, 0x79
        """,
        "102A 3333" + (" 0000" * (65536 - 4)) + " 9401 3579",
        ["line 6: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 3, 0xFFFE: 5, 0xFFFF: 6},
    ),
    (
        "branch label extreme negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0x0081
        b r4 _some_label # the label is at relative -0x80
        """,
        "102A 3333" + (" 0000" * (0x81 - 2)) + " 94FF",
        [],
        {0: 1, 1: 3, 0x0081: 5},
    ),
    (
        "branch label negative to undef",
        """\
        yield
        .label _some_label
        .offset 0x005
        b r4 _some_label # the label is at relative -4
        """,
        "102A 0000 0000 0000 0000 9483",
        [],
        {0: 1, 5: 4},
    ),
    (
        "branch label low positive",
        """\
        b r6 _some_label
        lw r2, 0x22
        .label _some_label
        lw r3, 0x33
        """,
        "9600 3222 3333",
        [],
        {0: 1, 1: 2, 2: 4},
    ),
    (
        "branch label medium positive",
        """\
        lw r3, 0x33
        b r7 _some_label
        lw r4, 0x44
        lw r5, 0x55
        lw r6, 0x66
        .label _some_label
        lw r7, 0x77
        """,
        "3333 9702 3444 3555 3666 3777",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 7},
    ),
    (
        "branch label barely-overflow positive",
        """\
        b r4 _some_label
        yield
        .offset 0xFFFF
        .label _some_label
        lw r3, 0x33
        """,
        "9480 102A" + (" 0000" * (65536 - 3)) + " 3333",
        ["line 5: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 2, 0xFFFF: 5},
    ),
    (
        "branch label overflow positive",
        """\
        lw r3, 0x33
        lw r4, 0x56
        b r4 _some_label # offset is -4
        yield
        .offset 0xFFFE
        .label _some_label
        lw r6, 0x66
        lw r2, 0x10
        """,
        "3333 3456 9483 102A" + (" 0000" * (65536 - 6)) + " 3666 3210",
        ["line 8: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 2, 2: 3, 3: 4, 0xFFFE: 7, 0xFFFF: 8},
    ),
    (
        "branch label extreme positive",
        """\
        lw r3, 0x33
        b r4 _some_label # the label is at relative +0x81
        lw r4, 0x56
        .offset 0x0082
        .label _some_label
        nop
        """,
        "3333 947F 3456" + (" 0000" * (0x82 - 3)) + " 5F00",
        [],
        {0: 1, 1: 2, 2: 3, 0x82: 6},
    ),
    (
        "branch label positive to undef",
        """\
        b r4 _some_label
        yield
        .offset 5
        .label _some_label
        """,
        "9403 102A",
        [],
        {0: 1, 1: 2},
    ),
    (
        "jump label low negative",
        """\
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        j _some_label
        """,
        "3210 3333 A800",
        [],
        {0: 1, 1: 3, 2: 4},
    ),
    (
        "jump label medium negative",
        """\
        .label _some_label
        lw r3, 0x33
        lw r4, 0x44
        lw r5, 0x55
        j _some_label
        """,
        "3333 3444 3555 A802",
        [],
        {0: 2, 1: 3, 2: 4, 3: 5},
    ),
    (
        "jump label barely-overflow negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFF
        j _some_label
        """,
        "102A 3333" + (" 0000" * (65536 - 3)) + " A000",
        ["line 5: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 3, 0xFFFF: 5},
    ),
    (
        "jump label overflow negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0xFFFE
        j _some_label
        lw r5, 0x79
        """,
        "102A 3333" + (" 0000" * (65536 - 4)) + " A001 3579",
        ["line 6: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 3, 0xFFFE: 5, 0xFFFF: 6},
    ),
    (
        "jump label extreme negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0x0801
        j _some_label # the label is at relative -0x800
        """,
        "102A 3333" + (" 0000" * (0x801 - 2)) + " AFFF",
        [],
        {0: 1, 1: 3, 0x0801: 5},
    ),
    (
        "jump label negative to undef",
        """\
        yield
        .label _some_label
        .offset 0x005
        j _some_label # the label is at relative -4
        """,
        "102A 0000 0000 0000 0000 A803",
        [],
        {0: 1, 5: 4},
    ),
    (
        "jump label low positive",
        """\
        j _some_label
        lw r2, 0x22
        .label _some_label
        lw r3, 0x33
        """,
        "A000 3222 3333",
        [],
        {0: 1, 1: 2, 2: 4},
    ),
    (
        "jump label medium positive",
        """\
        lw r3, 0x33
        j _some_label
        lw r4, 0x44
        lw r5, 0x55
        lw r6, 0x66
        .label _some_label
        lw r7, 0x77
        """,
        "3333 A002 3444 3555 3666 3777",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 7},
    ),
    (
        "jump label barely-overflow positive",
        """\
        j _some_label
        yield
        .offset 0xFFFF
        .label _some_label
        lw r3, 0x33
        """,
        "A800 102A" + (" 0000" * (65536 - 3)) + " 3333",
        ["line 5: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 2, 0xFFFF: 5},
    ),
    (
        "jump label overflow positive",
        """\
        lw r3, 0x33
        lw r4, 0x56
        j _some_label # offset is -4
        yield
        .offset 0xFFFE
        .label _some_label
        lw r6, 0x66
        lw r2, 0x10
        """,
        "3333 3456 A803 102A" + (" 0000" * (65536 - 6)) + " 3666 3210",
        ["line 8: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 2, 2: 3, 3: 4, 0xFFFE: 7, 0xFFFF: 8},
    ),
    (
        "jump label extreme positive",
        """\
        lw r3, 0x33
        j _some_label # the label is at relative +0x801
        lw r4, 0x56
        .offset 0x0802
        .label _some_label
        nop
        """,
        "3333 A7FF 3456" + (" 0000" * (0x802 - 3)) + " 5F00",
        [],
        {0: 1, 1: 2, 2: 3, 0x0802: 6},
    ),
    (
        "jump label positive to undef",
        """\
        j _some_label
        yield
        .offset 5
        .label _some_label
        """,
        "A003 102A",
        [],
        {0: 1, 1: 2},
    ),
    (
        "jump label offset, negative",
        """\
        lw r4, 0x56
        j _some_label +0x3  # Effective offset is +6
        yield
        lw r2, 0x10
        .label _some_label
        """,
        "3456 A004 102A 3210",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "jump label offset, positive",
        """\
        lw r4, 0x56
        .label _some_label
        yield
        lw r2, 0x10
        j _some_label -2  # Effective offset is -4
        """,
        "3456 102A 3210 A803",
        [],
        {0: 1, 1: 3, 2: 4, 3: 5},
    ),
    (
        "offset with label zero",
        """\
        .label _some_label
        .offset 3
        yield
        .offset _some_label
        lw r3, 0x33
        """,
        "3333 0000 0000 102A",
        [],
        {0: 5, 3: 3},
    ),
    (
        "offset with label nonzero",
        """\
        lw r2, 0x10
        .label _some_label
        .offset 3
        yield
        .offset _some_label
        lw r3, 0x33
        """,
        "3210 3333 0000 102A",
        [],
        {0: 1, 3: 4, 1: 6},
    ),
    (
        ".offset with label multi",
        """\
        lw r0, 0
        .label _some_label
        .offset _some_label
        .offset _some_label
        .offset _some_label
        .offset _some_label
        yield
        """,
        "3000 102A",
        [],
        {0: 1, 1: 7},
    ),
    (
        "hash zero",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E471
        """,
        "0000",
        [],
        dict(),
    ),
    (
        "hash zero lowercase",
        """\
        .assert_hash fa43239bcee7b97ca62f007cc68487560a39e19f74f3dde7486db3f98df8e471
        """,
        "0000",
        [],
        dict(),
    ),
    (
        "hash yield before",
        """\
        .assert_hash AE86FC31C317812B22F44972414587BB06FC0BE674129DF9AD783E2FBCB9050B
        yield
        """,
        "102A 0000",
        [],
        {0: 2},
    ),
    (
        "hash yield after",
        """\
        yield
        .assert_hash AE86FC31C317812B22F44972414587BB06FC0BE674129DF9AD783E2FBCB9050B
        """,
        "102A 0000",
        [],
        {0: 1},
    ),
    (
        "hash yield after, zero-word",
        """\
        yield
        .assert_hash AE86FC31C317812B22F44972414587BB06FC0BE674129DF9AD783E2FBCB9050B
        .word 0000
        """,
        "102A 0000",
        [],
        {0: 1, 1: 3},
    ),
    (
        "pseudo-instruction bgt immediate",
        """\
        bgt r1 r2 +45
        """,
        "8212 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bgt label",
        """\
        bgt r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "82EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bgts immediate",
        """\
        bgts r1 r2 +45
        """,
        "8312 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bgts label",
        """\
        bgts r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "83EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction beq immediate",
        """\
        beq r1 r2 +45
        """,
        "8412 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction beq label",
        """\
        beq r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "84EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bge immediate",
        """\
        bge r1 r2 +45
        """,
        "8612 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bge label",
        """\
        bge r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "86EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bges immediate",
        """\
        bges r1 r2 +45
        """,
        "8712 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bges label",
        """\
        bges r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "87EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction blt immediate",
        """\
        blt r1 r2 +45
        """,
        "8812 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction blt label",
        """\
        blt r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "88EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction blts immediate",
        """\
        blts r1 r2 +45
        """,
        "8912 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction blts label",
        """\
        blts r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "89EF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bne immediate",
        """\
        bne r1 r2 +45
        """,
        "8A12 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bne label",
        """\
        bne r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "8AEF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction ble immediate",
        """\
        ble r1 r2 +45
        """,
        "8C12 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction ble label",
        """\
        ble r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "8CEF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bles immediate",
        """\
        bles r1 r2 +45
        """,
        "8D12 922b",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction bles label",
        """\
        bles r14 r15 _dest
        .offset 0x15
        .label _dest
        """,
        "8DEF 9F12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "pseudo-instruction eqz",
        """\
        eqz r0
        eqz r6
        eqz r15
        """,
        "8400 8466 84FF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction nez",
        """\
        nez r0
        nez r6
        nez r15
        """,
        "8A00 8A66 8AFF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction ltsz",
        """\
        ltsz r0
        ltsz r6
        ltsz r15
        """,
        "8900 8966 89FF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction lesz",
        """\
        lesz r0
        lesz r6
        lesz r15
        """,
        "8D00 8D66 8DFF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction gtsz",
        """\
        gtsz r0
        gtsz r6
        gtsz r15
        """,
        "8300 8366 83FF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction gesz",
        """\
        gesz r0
        gesz r6
        gesz r15
        """,
        "8700 8766 87FF",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction beqz",
        """\
        beqz r0 +42
        beqz r6 +42
        beqz r15 +42
        """,
        "8400 9028 8466 9628 84FF 9F28",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3},
    ),
    (
        "pseudo-instruction bnez",
        """\
        bnez r0 +42
        bnez r6 +42
        bnez r15 +42
        """,
        "9028 9628 9F28",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "pseudo-instruction bltsz",
        """\
        bltsz r0 +42
        bltsz r6 +42
        bltsz r15 +42
        """,
        "8900 9028 8966 9628 89FF 9F28",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3},
    ),
    (
        "pseudo-instruction blesz",
        """\
        blesz r0 +42
        blesz r6 +42
        blesz r15 +42
        """,
        "8D00 9028 8D66 9628 8DFF 9F28",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3},
    ),
    (
        "pseudo-instruction bgtsz",
        """\
        bgtsz r0 +42
        bgtsz r6 +42
        bgtsz r15 +42
        """,
        "8300 9028 8366 9628 83FF 9F28",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3},
    ),
    (
        "pseudo-instruction bgesz",
        """\
        bgesz r0 +42
        bgesz r6 +42
        bgesz r15 +42
        """,
        "8700 9028 8766 9628 87FF 9F28",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3},
    ),
    (
        "pseudo-instruction bgesz to label",
        """\
        bgesz r0 _foo
        bgesz r6 _foo
        bgesz r15 _foo
        yield
        .label _foo
        """,
        "8700 9004 8766 9602 87FF 9F00 102A",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4},
    ),
    (
        "longbranch to label manual",
        """\
        eqz r0
        b r0 +2
        j _destination
        eqz r5
        b r5 +2
        j _destination
        .offset 0x300
        .label _destination
        """,
        "8400 9000 A2FC 8455 9500 A2F9",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "longbranch to label",
        """\
        lb r0 _destination
        lb r5 _destination
        .offset 0x300
        .label _destination
        """,
        "8400 9000 A2FC 8455 9500 A2F9",
        [
            "line 1: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
            "line 2: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
        ],
        {0: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2},
    ),
    (
        "longbranch condition tworeg, lbeq to imm positive",
        """\
        lbeq r0 r1 +0x123
        """,
        "8A01 9100 A121",
        [],
        {0: 1, 1: 1, 2: 1},
    ),
    (
        "longbranch condition tworeg, lbne to imm negative",
        """\
        lbne r10 r11 -0x234
        """,
        "84AB 9B00 AA33",
        [],
        {0: 1, 1: 1, 2: 1},
    ),
    (
        "longbranch condition tworeg, lblt to label forward positive",
        """\
        lblt r8 r9 _destination
        nop
        .offset 0xAA
        .label _destination
        """,
        # Note that this cannot be done in a single instruction, as `b` also carries a sign bit.
        "8689 9900 A0A6 5F00",
        [],
        {0: 1, 1: 1, 2: 1, 3: 2},
    ),
    (
        "longbranch condition tworeg, lbles to label forward negative",
        """\
        .offset 0x100
        lbles r6 r7 _destination
        nop
        .offset 0
        .label _destination
        """,
        "0000" * 0x100 + "8367 9700 A901 5F00",
        [],
        {0x100: 2, 0x101: 2, 0x102: 2, 0x103: 3},
    ),
    (
        "longbranch condition tworeg, lbgts to label backward positive",
        """\
        .offset 0x100
        .label _destination
        .offset 0
        lbgts r9 r3 _destination
        nop
        """,
        "8D93 9300 A0FC 5F00",
        [],
        {0: 4, 1: 4, 2: 4, 3: 5},
    ),
    (
        "longbranch condition tworeg, lbge to label backward negative",
        """\
        .label _destination
        .offset 0x400
        lbge r15 r14 _destination
        nop
        """,
        "0000" * 0x400 + "88FE 9E00 AC01 5F00",
        [],
        {0x400: 3, 0x401: 3, 0x402: 3, 0x403: 4},
    ),
    (
        "longbranch condition zero, lbltsz to imm positive",
        """\
        lbltsz r0 +0x123
        """,
        "8700 9000 A121",
        [],
        {0: 1, 1: 1, 2: 1},
    ),
    (
        "longbranch condition zero, lbeqz to imm positive",
        """\
        lbeqz r0 +0x123
        """,
        "9000 A121",
        [],
        {0: 1, 1: 1},
    ),
    (
        "longbranch condition zero, lbnez to imm negative",
        """\
        lbnez r10 -0x234
        """,
        "84AA 9A00 AA33",
        [],
        {0: 1, 1: 1, 2: 1},
    ),
    (
        "longbranch condition zero, lbltsz to label forward positive",
        """\
        lbltsz r8 _destination
        nop
        .offset 0xAA
        .label _destination
        """,
        # Note that this cannot be done in a single instruction, as `b` also carries a sign bit.
        "8788 9800 A0A6 5F00",
        [],
        {0: 1, 1: 1, 2: 1, 3: 2},
    ),
    (
        "longbranch condition zero, lblesz to label forward negative",
        """\
        .offset 0x100
        lblesz r6 _destination
        nop
        .offset 0
        .label _destination
        """,
        "0000" * 0x100 + "8366 9600 A901 5F00",
        [],
        {0x100: 2, 0x101: 2, 0x102: 2, 0x103: 3},
    ),
    (
        "longbranch condition zero, lbgtsz to label backward positive",
        """\
        .offset 0x100
        .label _destination
        .offset 0
        lbgtsz r9 _destination
        nop
        """,
        "8D99 9900 A0FC 5F00",
        [],
        {0: 4, 1: 4, 2: 4, 3: 5},
    ),
    (
        "longbranch condition zero, lbgesz to label backward negative",
        """\
        .label _destination
        .offset 0x400
        lbgesz r15 _destination
        nop
        """,
        "0000" * 0x400 + "89FF 9F00 AC01 5F00",
        [],
        {0x400: 3, 0x401: 3, 0x402: 3, 0x403: 4},
    ),
    (
        "branch condition zero, bnez optimization immediate",
        """\
        bnez r3 +10
        nop
        """,
        "9308 5F00",
        [],
        {0: 1, 1: 2},
    ),
    (
        "branch condition zero, bnez optimization label",
        """\
        bnez r12 _foo
        nop
        .offset 0x50
        .label _foo
        """,
        "9C4E 5F00",
        [],
        {0: 1, 1: 2},
    ),
    (
        "longbranch condition zero, lbeqz optimization immediate",
        """\
        lbeqz r3 +0xAA
        nop
        """,
        "9300 A0A8 5F00",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "longbranch condition zero, lbeqz optimization label",
        """\
        lbeqz r12 _foo
        nop
        .offset 0x123
        .label _foo
        """,
        "9C00 A120 5F00",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "jump register high",
        """\
        jhi r13 +0xEF00
        """,
        "CDEF",
        [],
        {0: 1},
    ),
    (
        "jump register high, no plus-sign",
        """\
        jhi r13 0xEF00
        """,
        "CDEF",
        [],
        {0: 1},
    ),
    (
        "jump register high, decimal, plus-sign",
        """\
        # This is difficult to read, don't do this!
        jhi r13 +61184
        """,
        "CDEF",
        [],
        {0: 2},
    ),
    (
        "jump register high, decimal, no plus-sign",
        """\
        # This is difficult to read, don't do this!
        jhi r13 61184
        """,
        "CDEF",
        [],
        {0: 2},
    ),
    (
        "jump register high, low decimal, no plus-sign",
        """\
        # This is difficult to read, don't do this!
        jhi r13 256
        """,
        "CD01",
        [],
        {0: 2},
    ),
    (
        "jump register high, three hexits",
        """\
        # This is difficult to read, don't do this!
        jhi r4 0x300
        """,
        "C403",
        [],
        {0: 2},
    ),
    (
        "jump register high, two hexits",
        """\
        # This is difficult to read, don't do this!
        jhi r4 0x00
        """,
        "C400",
        [],
        {0: 2},
    ),
    (
        "jump register high, one digit",
        """\
        # This is difficult to read, don't do this!
        jhi r4 0
        """,
        "C400",
        [],
        {0: 2},
    ),
    (
        "load address of label, backward",
        """\
        ill
        .label _foo
        .word 0xABCD
        la r7, _foo
        """,
        "FFFF ABCD 3701",
        [],
        {0: 1, 1: 3, 2: 4},
    ),
    (
        "load address of label, forward",
        """\
        la r7, _foo
        ill
        .label _foo
        """,
        "3702 FFFF",
        [],
        {0: 1, 1: 2},
    ),
    (
        "load address of label, forward max",
        """\
        .offset 2
        la r8, _foo
        .offset 0x007F
        .label _foo
        """,
        "0000 0000 387F",
        [],
        {2: 2},
    ),
    (
        "load address of label, forward min",
        """\
        .offset 2
        la r8, _foo
        .offset 0xFF80
        .label _foo
        """,
        "0000 0000 3880",
        [],
        {2: 2},
    ),
    (
        "load address of label, backward max",
        """\
        .offset 0x007F
        .label _foo
        .offset 2
        la r9, _foo
        """,
        "0000 0000 397F",
        [],
        {2: 4},
    ),
    (
        "load address of label, backward min",
        """\
        .offset 0xFF80
        .label _foo
        .offset 2
        la r9, _foo
        """,
        "0000 0000 3980",
        [],
        {2: 4},
    ),


    (
        "long load address of label, backward",
        """\
        .offset 0x1234
        .label _foo
        .offset 1
        .word 0xABCD
        lla r7, _foo
        """,
        "0000 ABCD 3734 4712",
        [],
        {1: 4, 2: 5, 3: 5},
    ),
    (
        "long load address of label, forward",
        """\
        lla r7, _foo
        .offset 0x20AC
        .label _foo
        """,
        "37AC 4720",
        [],
        {0: 1, 1: 1},
    ),
    (
        "long load address of label, forward max pos",
        """\
        .offset 2
        lla r8, _foo
        .offset 0x7FFF
        .label _foo
        """,
        "0000 0000 38FF 487F",
        [],
        {2: 2, 3: 2},
    ),
    (
        "long load address of label, forward max neg",
        """\
        .offset 1
        lla r9, _foo
        .offset 0x8000
        .label _foo
        """,
        "0000 3900 4980",
        [],
        {1: 2, 2: 2},
    ),
    (
        "long load address of label, backward max pos",
        """\
        .offset 0x7FFF
        .label _foo
        .offset 1
        lla r6, _foo
        """,
        "0000 36FF 467F",
        [],
        {1: 4, 2: 4},
    ),
    (
        "long load address of label, backward max neg",
        """\
        .offset 0x8000
        .label _foo
        .offset 1
        lla r0, _foo
        """,
        "0000 3000 4080",
        [],
        {1: 4, 2: 4},
    ),
    (
        "long load address of label, forward max pos one-insn nowarn",  # no backward sibling
        """\
        .offset 0
        lla r10, _foo
        .offset 0x007F
        .label _foo
        """,
        "3A7F 4A00",
        [],  # no warning: Still in slack-region
        {0: 2, 1: 2},
    ),
    (
        "long load address of label, backward max neg one-insn nowarn",  # no forward sibling
        """\
        .offset 0xFF80
        .label _foo
        .offset 0
        lla r9, _foo
        """,
        "3980 49FF",
        [],  # no warning: Still in slack-region
        {0: 4, 1: 4},
    ),
    (
        "long load address of label, backward min pos one-insn nowarn",  # no forward sibling
        """\
        .offset 0x0076
        .label _foo
        .offset 0
        lla r13, _foo
        """,
        "3D76 4D00",
        [],  # no warning: barely in slack-region
        {0: 4, 1: 4},
    ),
    (
        "long load address of label, forward min neg one-insn nowarn",  # no backward sibling
        """\
        .offset 0
        lla r7, _foo
        .offset 0xFF89
        .label _foo
        """,
        "3789 47FF",
        [],  # no warning: barely in slack-region
        {0: 2, 1: 2},
    ),
    (
        "long load address of label, backward max neg one-insn warn",  # no forward sibling
        """\
        .offset 0xFF8A
        .label _foo
        .offset 0
        lla r1, _foo
        """,
        "318A 41FF",
        [
            "line 4: Pseudo-instruction 'lla' (to _foo)' supports labels in the full range, but was used for just a short offset of 0xFF8A. Try using the non-long version, which uses fewer instructions. (non-fatal)"
        ],
        {0: 4, 1: 4},
    ),
    (
        "long load address of label, forward max pos one-insn warn",  # no backward sibling
        """\
        .offset 0
        lla r4, _foo
        .offset 0x0075
        .label _foo
        """,
        "3475 4400",
        [
            "line 2: Pseudo-instruction 'lla' (to _foo)' supports labels in the full range, but was used for just a short offset of 0x0075. Try using the non-long version, which uses fewer instructions. (non-fatal)"
        ],
        {0: 2, 1: 2},
    ),
    (
        "long load address of label, backward min neg one-insn warn",  # no forward sibling
        """\
        .offset 0xFFFF
        .label _foo
        .offset 0
        lla r0, _foo
        """,
        "30FF 40FF",
        [
            "line 4: Pseudo-instruction 'lla' (to _foo)' supports labels in the full range, but was used for just a short offset of 0xFFFF. Try using the non-long version, which uses fewer instructions. (non-fatal)"
        ],
        {0: 4, 1: 4},
    ),
    (
        "long load address of label, forward min pos one-insn warn",  # no backward sibling
        """\
        .offset 0
        lla r9, _foo
        .offset 0  # lol
        .label _foo
        """,
        "3900 4900",
        [
            "line 2: Pseudo-instruction 'lla' (to _foo)' supports labels in the full range, but was used for just a short offset of 0x0000. Try using the non-long version, which uses fewer instructions. (non-fatal)"
        ],
        {0: 2, 1: 2},
    ),
    (
        "long load address of label, forward min pos-non-zero one-insn warn",  # no backward sibling
        """\
        .offset 0
        lla r2, _foo
        .offset 1
        .label _foo
        """,
        "3201 4200",
        [
            "line 2: Pseudo-instruction 'lla' (to _foo)' supports labels in the full range, but was used for just a short offset of 0x0001. Try using the non-long version, which uses fewer instructions. (non-fatal)"
        ],
        {0: 2, 1: 2},
    ),
]

NEGATIVE_TESTS = [
    (
        "garbage",
        """\
        garbage
        """,
        [
            "line 1: Command 'garbage' not found. Close match: bge",
        ],
    ),
    (
        "yield with arg",
        """\
        yield 42
        """,
        [
            "line 1: Command 'yield' does not take any arguments (expected end of line, found '42' instead)"
        ],
    ),
    (
        "late garbage",
        """\
        yield
        garbage
        """,
        [
            "line 2: Command 'garbage' not found. Close match: bge",
        ],
    ),
    (
        "bless",
        """\
        bless
        """,
        [
            "line 1: Command 'bless' not found. Close matches: bles, lbles, blesz",
        ],
    ),
    (
        "unrecognizable",
        """\
        unrecognizable r3 r4
        """,
        [
            "line 1: Command 'unrecognizable' not found.",
        ],
    ),
    (
        "cxz",
        """\
        cxz r9
        """,
        [
            "line 1: Command 'cxz' not found. Close matches: ctz, clz",
        ],
    ),
    (
        "late yield with arg",
        """\
        yield
        yield 42
        """,
        [
            "line 2: Command 'yield' does not take any arguments (expected end of line, found '42' instead)"
        ],
    ),
    (
        "CPUID with arg",
        """\
        cpuid 42
        """,
        [
            "line 1: Command 'cpuid' does not take any arguments (expected end of line, found '42' instead)"
        ],
    ),
    (
        "Debug-dump with arg",
        """\
        debug 1337
        """,
        [
            "line 1: Command 'debug' does not take any arguments (expected end of line, found '1337' instead)"
        ],
    ),
    (
        "Time with arg",
        """\
        time 0x42
        """,
        [
            "line 1: Command 'time' does not take any arguments (expected end of line, found '0x42' instead)"
        ],
    ),
    (
        "nop with arg imm",
        """\
        nop 0x42
        """,
        [
            "line 1: Command 'nop' does not take any arguments (expected end of line, found '0x42' instead)"
        ],
    ),
    (
        "nop with arg reg",
        """\
        nop r5
        """,
        [
            "line 1: Command 'nop' does not take any arguments (expected end of line, found 'r5' instead)"
        ],
    ),
    (
        "Store word no arg",
        """\
        sw
        """,
        [
            "line 1: Command 'sw' expects exactly two comma-separated arguments, got [''] instead."
        ],
    ),
    (
        "Store word one arg",
        """\
        sw r4
        """,
        [
            "line 1: Command 'sw' expects exactly two comma-separated arguments, got ['r4'] instead."
        ],
    ),
    (
        "Store word no comma",
        """\
        sw r4 r4
        """,
        [
            "line 1: Command 'sw' expects exactly two comma-separated arguments, got ['r4 r4'] instead."
        ],
    ),
    (
        "Store word too many",
        """\
        sw r4, r4, r4
        """,
        [
            "line 1: Command 'sw' expects exactly two comma-separated arguments, got ['r4', 'r4', 'r4'] instead."
        ],
    ),
    (
        "Store word illegal register",
        """\
        sw r16, r1
        """,
        [
            "line 1: Cannot parse register for first argument to sw: Expected register with index in 0,1,…,15, instead got 'r16'. Try something like 'r0' instead."
        ],
    ),
    (
        "Store word other illegal register",
        """\
        sw r4, r16
        """,
        [
            "line 1: Cannot parse register for second argument to sw: Expected register with index in 0,1,…,15, instead got 'r16'. Try something like 'r0' instead."
        ],
    ),
    (
        "Store word underscore register",
        """\
        sw r1_3, r1
        """,
        [
            "line 1: Cannot parse register for first argument to sw: Refusing underscores in register index 'r1_3'. Try something like 'r0' instead."
        ],
    ),
    (
        "Store word immediate address",
        # FIXME: This would be a nifty feature though!
        """\
        sw 0x1234, r1
        """,
        [
            "line 1: Cannot parse register for first argument to sw: Expected register (beginning with 'r'), instead got '0x1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "Store word immediate value",
        """\
        sw r4, 0x1234
        """,
        [
            "line 1: Cannot parse register for second argument to sw: Expected register (beginning with 'r'), instead got '0x1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "Load word instruction immediate value",
        """\
        lwi 0x1234, r4
        """,
        [
            "line 1: Cannot parse register for first argument to lwi: Expected register (beginning with 'r'), instead got '0x1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "Load word instruction immediate address",
        # FIXME: This should be a feature!
        """\
        lwi r5, 0x1234
        """,
        [
            "line 1: Cannot parse register for second argument to lwi: Expected register (beginning with 'r'), instead got '0x1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "Load word instruction three-arg",
        """\
        lwi r1, r2, r3
        """,
        [
            "line 1: Command 'lwi' expects exactly two arguments, got ['r1', 'r2', 'r3'] instead."
        ],
    ),
    (
        "Load word data three-arg",
        """\
        lw r1, r2, r3
        """,
        [
            "line 1: Command 'lw' expects exactly two arguments, got ['r1', 'r2', 'r3'] instead."
        ],
    ),
    (
        "Load word data immediate value",
        """\
        lw 0x1234, r5
        """,
        [
            "line 1: Cannot parse register for first argument to lw: Expected register (beginning with 'r'), instead got '0x1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "Load word data immediate (too low)",
        """\
        lw r1, -0x8001
        """,
        [
            "line 1: Cannot parse register for second argument to lw: Expected register (beginning with 'r'), instead got '-0x8001'. Try something like 'r0' instead.",
            "line 1: Immediate value -32769 (hex: -8001) in second argument to lw is out of bounds [-0x8000, 0xFFFF]",
        ],
    ),
    (
        "Load word data immediate (too high)",
        """\
        lw r0, 65536
        """,
        [
            "line 1: Cannot parse register for second argument to lw: Expected register (beginning with 'r'), instead got '65536'. Try something like 'r0' instead.",
            "line 1: Immediate value 65536 (hex: +10000) in second argument to lw is out of bounds [-0x8000, 0xFFFF]",
        ],
    ),
    (
        "Load word data immediate (garbage)",
        """\
        lw r0, garbage
        """,
        [
            "line 1: Cannot parse register for second argument to lw: Expected register (beginning with 'r'), instead got 'garbage'. Try something like 'r0' instead.",
            "line 1: Cannot parse immediate for second argument to lw: Expected integer number, instead got 'garbage'. Try something like '42', '0xABCD', or '-0x123' instead.",
        ],
    ),
    (
        "Load word data immediate three-arg",
        """\
        lhi r1, r2, r3
        """,
        [
            "line 1: Command 'lhi' expects exactly two arguments, got ['r1', 'r2', 'r3'] instead."
        ],
    ),
    (
        "Load word data immediate high-only from register",
        """\
        lhi r0, r1
        """,
        [
            "line 1: Cannot parse immediate for second argument to lhi: Expected integer number, instead got 'r1'. Try something like '42', '0xABCD', or '-0x123' instead."
        ],
    ),
    (
        "Load word data immediate high-only invalid",
        """\
        lhi r0, 0x1234
        """,
        [
            "line 1: Unsure how to load the high byte of a two-byte word 0x1234. Specify the byte either as 0xAB00 or as 0xAB instead."
        ],
    ),
    (
        "decr no args",
        """\
        decr
        """,
        [
            "line 1: Command 'decr' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "decr too many args",
        """\
        decr r1, r2, r3
        """,
        [
            "line 1: Command 'decr' expects either one or two register arguments, got ['r1', 'r2', 'r3'] instead."
        ],
    ),
    (
        "decr 1-arg, imm",
        """\
        decr 0x123
        """,
        [
            "line 1: Cannot parse register for argument #1 (1-indexed) to decr: Expected register (beginning with 'r'), instead got '0x123'. Try something like 'r0' instead."
        ],
    ),
    (
        "decr 2-arg, imm reg",
        """\
        decr 123, r0
        """,
        [
            "line 1: Cannot parse register for argument #1 (1-indexed) to decr: Expected register (beginning with 'r'), instead got '123'. Try something like 'r0' instead."
        ],
    ),
    (
        "decr 2-arg, reg imm",
        """\
        decr r0, 123
        """,
        [
            "line 1: Cannot parse register for argument #2 (1-indexed) to decr: Expected register (beginning with 'r'), instead got '123'. Try something like 'r0' instead."
        ],
    ),
    (
        "incr no args",
        """\
        incr
        """,
        [
            "line 1: Command 'incr' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "not no args",
        """\
        not
        """,
        [
            "line 1: Command 'not' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "clz no args",
        """\
        clz
        """,
        [
            "line 1: Command 'clz' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "ctz no args",
        """\
        ctz
        """,
        [
            "line 1: Command 'ctz' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "rnd no args",
        """\
        rnd
        """,
        [
            "line 1: Command 'rnd' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "mov no args",
        """\
        mov
        """,
        [
            "line 1: Command 'mov' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "popcnt no args",
        """\
        popcnt
        """,
        [
            "line 1: Command 'popcnt' expects either one or two register arguments, got none instead."
        ],
    ),
    (
        "add comma space",
        """\
        add r4, r5
        """,
        [
            "line 1: Cannot parse register for argument #1 (1-indexed) to add: Expected register with numeric index, instead got 'r4,'. Try something like 'r0' instead."
        ],
    ),
    (
        "add comma nospace",
        """\
        add r4,r5
        """,
        [
            "line 1: Command 'add' expects exactly two space-separated register arguments, got ['r4,r5'] instead."
        ],
    ),
    (
        "add three args",
        """\
        add r4 r5 r6
        """,
        [
            "line 1: Cannot parse register for argument #2 (1-indexed) to add: Expected register with numeric index, instead got 'r5 r6'. Try something like 'r0' instead."
        ],
    ),
    (
        "add noargs",
        """\
        add
        """,
        [
            "line 1: Command 'add' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "add space comma space",
        """\
        add r4 , r5
        """,
        [
            "line 1: Cannot parse register for argument #2 (1-indexed) to add: Expected register (beginning with 'r'), instead got ', r5'. Try something like 'r0' instead."
        ],
    ),
    (
        "sub noargs",
        """\
        sub
        """,
        [
            "line 1: Command 'sub' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "mul noargs",
        """\
        mul
        """,
        [
            "line 1: Command 'mul' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "mulh noargs",
        """\
        mulh
        """,
        [
            "line 1: Command 'mulh' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "divu noargs",
        """\
        divu
        """,
        [
            "line 1: Command 'divu' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "divs noargs",
        """\
        divs
        """,
        [
            "line 1: Command 'divs' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "modu noargs",
        """\
        modu
        """,
        [
            "line 1: Command 'modu' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "mods noargs",
        """\
        mods
        """,
        [
            "line 1: Command 'mods' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "and noargs",
        """\
        and
        """,
        [
            "line 1: Command 'and' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "or noargs",
        """\
        or
        """,
        [
            "line 1: Command 'or' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "xor noargs",
        """\
        xor
        """,
        [
            "line 1: Command 'xor' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "sl noargs",
        """\
        sl
        """,
        [
            "line 1: Command 'sl' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "srl noargs",
        """\
        srl
        """,
        [
            "line 1: Command 'srl' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "sra noargs",
        """\
        sra
        """,
        [
            "line 1: Command 'sra' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "lt noargs",
        """\
        lt
        """,
        [
            "line 1: Command 'lt' expects exactly two space-separated register arguments, got [''] instead."
        ],
    ),
    (
        "le one-arg",
        """\
        le r3
        """,
        [
            "line 1: Command 'le' expects exactly two space-separated register arguments, got ['r3'] instead."
        ],
    ),
    (
        "gt reg imm",
        """\
        gt r4 1234
        """,
        [
            "line 1: Cannot parse register for argument #2 (1-indexed) to gt: Expected register (beginning with 'r'), instead got '1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "ge imm reg",
        """\
        ge 1234 r5
        """,
        [
            "line 1: Cannot parse register for argument #1 (1-indexed) to ge: Expected register (beginning with 'r'), instead got '1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "eq comma-arg",
        """\
        eq r3, r5
        """,
        [
            "line 1: Cannot parse register for argument #1 (1-indexed) to eq: Expected register with numeric index, instead got 'r3,'. Try something like 'r0' instead."
        ],
    ),
    (
        "ne three-arg",
        """\
        ne r3 r4 r5
        """,
        [
            "line 1: Cannot parse register for argument #2 (1-indexed) to ne: Expected register with numeric index, instead got 'r4 r5'. Try something like 'r0' instead."
        ],
    ),
    (
        "eq same-arg",
        """\
        eq r0 r0
        """,
        [
            "line 1: Command 'eq' requires two different registers to be used, got ['r0', 'r0'] instead."
        ],
    ),
    (
        "gts same-arg",
        """\
        gts r5 r5
        """,
        [
            "line 1: Command 'gts' requires two different registers to be used, got ['r5', 'r5'] instead."
        ],
    ),
    (
        "branch comma",
        """\
        b r5, 5
        """,
        [
            "line 1: Cannot parse register for first argument to b: Expected register with numeric index, instead got 'r5,'. Try something like 'r0' instead."
        ],
    ),
    (
        "branch too large",
        """\
        b r5 130
        """,
        [
            "line 1: Command 'b' can only branch by offsets in [-128, 129], but not by 130. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
        ],
    ),
    (
        "branch too negative",
        """\
        b r10 -129
        """,
        [
            "line 1: Command 'b' can only branch by offsets in [-128, 129], but not by -129. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
        ],
    ),
    (
        "branch single arg",
        """\
        b r10
        """,
        [
            "line 1: Command 'b' expects exactly two space-separated register arguments, got ['r10'] instead."
        ],
    ),
    (
        "branch to reg",
        """\
        b r10 r5
        """,
        [
            "line 1: Cannot parse immediate for second argument to b: Expected integer number, instead got 'r5'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for second argument to b must start with a '_' and contain at least two characters, found name 'r5' instead",
        ],
    ),
    (
        "branch by 0",
        """\
        b r10 0
        """,
        [
            "line 1: Command 'b' cannot encode an infinite loop (offset 0). Try using 'j reg' instead."
        ],
    ),
    (
        "branch by 1",
        """\
        b r10 1
        """,
        [
            "line 1: Command 'b' cannot encode the nop-branch (offset 1). Try using 'nop' instead."
        ],
    ),
    (
        "jump noarg",
        """\
        j
        """,
        ["line 1: Command 'j' expects either one or two arguments, got none instead."],
    ),
    (
        "jump two arg immediate, comma",
        """\
        j 0x12, 0x34
        """,
        [
            "line 1: Cannot parse register for first argument to two-arg-j: Expected register (beginning with 'r'), instead got '0x12,'. Try something like 'r0' instead.",
            "line 1: Label name for first argument to two-arg-j must start with a '_' and contain at least two characters, found name '0x12,' instead",
            "line 1: Command 'j' with two arguments expects either register or label for first argument, got '0x12,' instead. Note that offsets have to use a space, like 'r4 +5'.",
        ],
    ),
    (
        "jump two arg immediate, space",
        """\
        j 0x12 0x34
        """,
        [
            "line 1: Cannot parse register for first argument to two-arg-j: Expected register (beginning with 'r'), instead got '0x12'. Try something like 'r0' instead.",
            "line 1: Label name for first argument to two-arg-j must start with a '_' and contain at least two characters, found name '0x12' instead",
            "line 1: Command 'j' with two arguments expects either register or label for first argument, got '0x12' instead. Note that offsets have to use a space, like 'r4 +5'.",
        ],
    ),
    (
        "jump by immediate extreme positive",
        """\
        j 0x802
        """,
        [
            "line 1: Command 'j' can only branch by offsets in [-2048, 2049], but not by 2050. Some commands support longer jumps, try 'lj' instead. Or try manually loading the address into a register first."
        ],
    ),
    (
        "jump by immediate extreme negative",
        """\
        j -0x801
        """,
        [
            "line 1: Command 'j' can only branch by offsets in [-2048, 2049], but not by -2049. Some commands support longer jumps, try 'lj' instead. Or try manually loading the address into a register first."
        ],
    ),
    (
        "jump to register onearg",
        """\
        j r16
        """,
        [
            "line 1: Cannot parse register for first argument of one-arg-j: Expected register with index in 0,1,…,15, instead got 'r16'. Try something like 'r0' instead.",
            "line 1: Cannot parse immediate for first argument of one-arg-j: Expected integer number, instead got 'r16'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for first argument of one-arg-j must start with a '_' and contain at least two characters, found name 'r16' instead",
            "line 1: Command 'j' with a single argument expects either immediate, register, or label, got 'r16' instead. Note that offsets have to use a space, like 'r4 +5'.",
        ],
    ),
    (
        "jump to register twoarg extreme positive",
        """\
        j r3 +128
        """,
        [
            "line 1: Command 'j' can only branch by offsets in [-128, 127], but not by 128. Try manually loading the final address into a register first."
        ],
    ),
    (
        "jump to register twoarg extreme negative",
        """\
        j r8 -129
        """,
        [
            "line 1: Command 'j' can only branch by offsets in [-128, 127], but not by -129. Try manually loading the final address into a register first."
        ],
    ),
    (
        "offset negative",
        """\
        .offset -1
        """,
        [
            "line 1: Immediate argument to '.offset' must be positive, found '-1' instead"
        ],
    ),
    (
        "offset overwrite",
        """\
        yield
        .offset 0
        yield
        """,
        ["line 3: Attempted to overwrite word 0x102A at 0x0000 with 0x102A."],
    ),
    (
        "offset overwrite indirect",
        """\
        .offset 2
        lw r4, 0x56
        .offset 0
        yield
        yield
        yield # Bam!
        """,
        ["line 6: Attempted to overwrite word 0x3456 at 0x0002 with 0x102A."],
    ),
    (
        "literal too positive",
        """\
        .word 65536
        """,
        [
            "line 1: Immediate value 65536 (hex: +10000) in argument of .word is out of bounds [-0x8000, 0xFFFF]"
        ],
    ),
    (
        "literal too negative decimal",
        """\
        .word -32769
        """,
        [
            "line 1: Immediate value -32769 (hex: -8001) in argument of .word is out of bounds [-0x8000, 0xFFFF]"
        ],
    ),
    (
        "literal too negative hex",
        """\
        .word -0x8001
        """,
        [
            "line 1: Immediate value -32769 (hex: -8001) in argument of .word is out of bounds [-0x8000, 0xFFFF]"
        ],
    ),
    (
        "mov single-arg",
        """\
        mov r0
        """,
        [
            "line 1: Refusing noop-mov: This does nothing, and is likely an error. Use '.word 5F00' or 'nop' instead."
        ],
    ),
    (
        "mov noop",
        """\
        mov r1, r1
        """,
        [
            "line 1: Refusing noop-mov: This does nothing, and is likely an error. Use '.word 5F11' or 'nop' instead."
        ],
    ),
    (
        "overwrite zeros",
        """\
        .word 0x0000
        .offset 0
        .word 0x0000
        """,
        ["line 3: Attempted to overwrite word 0x0000 at 0x0000 with 0x0000."],
    ),
    (
        "label no name",
        """\
        .label
        """,
        [
            "line 1: Directive '.label' takes exactly one argument (the literal label name), found nothing instead"
        ],
    ),
    (
        "label two-arg",
        """\
        .label _foo _bar
        """,
        [
            "line 1: Directive '.label' takes exactly one argument (the literal label name), found ['_foo', '_bar'] instead"
        ],
    ),
    (
        "label bad name",
        """\
        .label 1234
        """,
        [
            "line 1: Label name for argument of .label must start with a '_' and contain at least two characters, found name '1234' instead"
        ],
    ),
    (
        "label no underscore",
        """\
        .label foobar
        """,
        [
            "line 1: Label name for argument of .label must start with a '_' and contain at least two characters, found name 'foobar' instead"
        ],
    ),
    (
        "label too short",
        """\
        .label _
        """,
        [
            "line 1: Label name for argument of .label must start with a '_' and contain at least two characters, found name '_' instead"
        ],
    ),
    (
        "label multidef",
        """\
        .label _hello_world
        yield
        .label _hello_world
        """,
        [
            "line 3: Label '_hello_world' previously defined in line 1 (old offset 0x0000, new offset 0x0001)"
        ],
    ),
    (
        "label multidef same offset",
        """\
        .label _hello_world
        .label _hello_world
        """,
        [
            "line 2: Label '_hello_world' previously defined in line 1 (old offset 0x0000, new offset 0x0000)"
        ],
    ),
    (
        "label special $",
        """\
        .label _$hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_$hello_world' instead"
        ],
    ),
    (
        "label special %",
        """\
        .label _%hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_%hello_world' instead"
        ],
    ),
    (
        "label special &",
        """\
        .label _&hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_&hello_world' instead"
        ],
    ),
    (
        "label special (",
        """\
        .label _(hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_(hello_world' instead"
        ],
    ),
    (
        "label special )",
        """\
        .label _)hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_)hello_world' instead"
        ],
    ),
    (
        "label special =",
        """\
        .label _=hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_=hello_world' instead"
        ],
    ),
    (
        "label special single quote",
        """\
        .label _'hello_world
        """,
        [
            # TODO: Escape it maybe?
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_'hello_world' instead"
        ],
    ),
    (
        "label special double quote",
        """\
        .label _"hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_\"hello_world' instead"
        ],
    ),
    (
        "label special [",
        """\
        .label _[hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_[hello_world' instead"
        ],
    ),
    (
        "label special ]",
        """\
        .label _]hello_world
        """,
        [
            "line 1: Label name for argument of .label must not contain any special characters ($%&()='\"[]), found name '_]hello_world' instead"
        ],
    ),
    (
        "branch unknown label",
        """\
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        b r4 _wrong_label
        """,
        [
            "line 5: Found end of asm text, but some forward references are unresolved: line 4 at offset 2 references label _wrong_label",
            "line 5: Did you mean any of these defined labels? ['_some_label']",
            "line 5: Unused label(s), try using them in dead code, or commenting them out: '_some_label' (line 2, offset 1)",
        ],
    ),
    (
        "branch label zero",
        """\
        lw r2, 0x10
        .label _some_label
        b r4 _some_label
        """,
        [
            "line 3: Command 'b (to label _some_label=0x0001, defined in line 2)' cannot encode an infinite loop (offset 0). Try using 'j reg' instead."
        ],
    ),
    (
        "branch label one",
        """\
        lw r2, 0x10
        b r4 _some_label
        .label _some_label
        lw r2, 0x10
        """,
        [
            "line 2: Command 'b (to label _some_label=0x0002, defined in line 3)' cannot encode the nop-branch (offset 1). Try using 'nop' instead.",
            "line 3: When label _some_label was defined.",
        ],
    ),
    (
        "branch label one overflow",
        """\
        .label _some_label
        lw r2, 0x10
        .offset 0xFFFF
        b r4 _some_label
        """,
        [
            "line 4: Command 'b (to label _some_label=0x0000, defined in line 1)' cannot encode the nop-branch (offset 1). Try using 'nop' instead."
        ],
    ),
    (
        "branch label too extreme negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0x0082
        b r4 _some_label # the label is at relative -0x81
        """,
        [
            "line 5: Command 'b (to label _some_label=0x0001, defined in line 2)' can only branch by offsets in [-128, 129], but not by -129. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
        ],
    ),
    (
        "branch label too extreme positive",
        """\
        lw r3, 0x33
        b r4 _some_label # the label is at relative +0x82
        lw r4, 0x56
        .offset 0x0083
        .label _some_label
        nop
        """,
        [
            "line 2: Command 'b (to label _some_label=0x0083, defined in line 5)' can only branch by offsets in [-128, 129], but not by 130. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction.",
            "line 5: When label _some_label was defined.",
        ],
    ),
    (
        "branch label zero after the fact",
        """\
        lw r2, 0x10
        b r4 _some_label
        .offset 1
        .label _some_label
        """,
        [
            "line 2: Command 'b (to label _some_label=0x0001, defined in line 4)' cannot encode an infinite loop (offset 0). Try using 'j reg' instead.",
            "line 4: When label _some_label was defined.",
        ],
    ),
    (
        "branch label one already defined",
        """\
        .offset 2
        .label _some_label
        .offset 0
        lw r2, 0x10
        b r4 _some_label
        lw r2, 0x10
        """,
        [
            "line 5: Command 'b (to label _some_label=0x0002, defined in line 2)' cannot encode the nop-branch (offset 1). Try using 'nop' instead.",
        ],
    ),
    (
        "jump label nonexistent",
        """\
        lw r2, 0x10
        .label _some_label
        lw r3, 0x33
        j _wrong_label
        """,
        [
            "line 5: Found end of asm text, but some forward references are unresolved: line 4 at offset 2 references label _wrong_label",
            "line 5: Did you mean any of these defined labels? ['_some_label']",
            "line 5: Unused label(s), try using them in dead code, or commenting them out: '_some_label' (line 2, offset 1)",
        ],
    ),
    (
        "jump label extreme negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0x0802
        j _some_label # the label is at relative -0x801
        """,
        [
            "line 5: Command 'j (to _some_label +0 = by -2049)' can only branch by offsets in [-2048, 2049], but not by -2049. Some commands support longer jumps, try 'lj (to _some_label +0 = by -2049)' instead. Or try manually loading the address into a register first."
        ],
    ),
    (
        "jump label extreme positive",
        """\
        lw r3, 0x33
        j _some_label # the label is at relative +0x801
        lw r4, 0x56
        .offset 0x0803
        .label _some_label
        nop
        """,
        [
            "line 2: Command 'j (to _some_label +0 = by +2050)' can only branch by offsets in [-2048, 2049], but not by 2050. Some commands support longer jumps, try 'lj (to _some_label +0 = by +2050)' instead. Or try manually loading the address into a register first.",
            "line 5: When label _some_label was defined.",
        ],
    ),
    (
        "jump label zero",
        """\
        .label _some_label
        j _some_label
        """,
        [
            "line 2: Command 'j (to _some_label +0 = by +0)' cannot encode an infinite loop (offset 0). Try jumping to a register instead."
        ],
    ),
    (
        "jump label one",
        """\
        j _some_label
        .label _some_label
        yield
        """,
        [
            "line 1: Command 'j (to _some_label +0 = by +1)' cannot encode the nop-jump (offset 1). Try using 'nop' instead.",
            "line 2: When label _some_label was defined.",
        ],
    ),
    (
        "jump label offset extreme negative",
        """\
        yield
        .label _some_label
        lw r3, 0x33
        .offset 0x0801
        j _some_label -1 # the label is at relative -0x801
        """,
        [
            "line 5: Command 'j (to _some_label -1 = by -2049)' can only branch by offsets in [-2048, 2049], but not by -2049. Some commands support longer jumps, try 'lj (to _some_label -1 = by -2049)' instead. Or try manually loading the address into a register first."
        ],
    ),
    (
        "jump label offset extreme positive",
        """\
        lw r3, 0x33
        j _some_label +1 # the label is at relative +0x801
        lw r4, 0x56
        .offset 0x0802
        .label _some_label
        nop
        """,
        [
            "line 2: Command 'j (to _some_label +1 = by +2050)' can only branch by offsets in [-2048, 2049], but not by 2050. Some commands support longer jumps, try 'lj (to _some_label +1 = by +2050)' instead. Or try manually loading the address into a register first.",
            "line 5: When label _some_label was defined.",
        ],
    ),
    (
        "jump label offset zero",
        """\
        j _some_label -2
        yield
        .label _some_label
        lw r3, 0x33
        """,
        [
            "line 1: Command 'j (to _some_label -2 = by +0)' cannot encode an infinite loop (offset 0). Try jumping to a register instead.",
            "line 3: When label _some_label was defined.",
        ],
    ),
    (
        "jump label offset one",
        """\
        j _some_label -1
        yield
        .label _some_label
        lw r3, 0x33
        """,
        [
            "line 1: Command 'j (to _some_label -1 = by +1)' cannot encode the nop-jump (offset 1). Try using 'nop' instead.",
            "line 3: When label _some_label was defined.",
        ],
    ),
    (
        "offset with label unknown",
        """\
        lw r0, 0
        .label _some_label
        .offset _wrong_label
        """,
        [
            "line 3: Label argument to '.offset' must be an already-delared label, found unknown label '_wrong_label' instead",
            "line 3: The already-defined labels are: ['_some_label']",
        ],
    ),
    (
        "offset with label overwrite",
        """\
        lw r0, 0
        .label _some_label
        yield
        .offset _some_label
        lw r1, 1
        """,
        ["line 5: Attempted to overwrite word 0x102A at 0x0001 with 0x3101."],
    ),
    (
        "hash zero invalid char",
        """\
        .assert_hash GA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E47
        """,
        [
            "line 1: Argument to .assert_hash must be a single 64-char hexstring of the expected SHA256, found instead 'GA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E47'."
        ],
    ),
    (
        "hash zero too short",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E47
        """,
        [
            "line 1: Argument to .assert_hash must be a single 64-char hexstring of the expected SHA256, found instead 'FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E47'."
        ],
    ),
    (
        "hash zero too long",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E4711
        """,
        [
            "line 1: Argument to .assert_hash must be a single 64-char hexstring of the expected SHA256, found instead 'FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E4711'."
        ],
    ),
    (
        "hash zero wrong",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E472
        """,
        [
            "line 2: Compilation successful, but encountered hash mismatch: line 1 expects hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E472, but created hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E471 instead."
        ],
    ),
    (
        "hash zero multi",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E471
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E471
        """,
        ["line 2: Expected hash already stated in line 1."],
    ),
    (
        "hash zero contradict",
        """\
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E471
        .assert_hash FA43239BCEE7B97CA62F007CC68487560A39E19F74F3DDE7486DB3F98DF8E472
        """,
        ["line 2: Expected hash already stated in line 1."],
    ),
    (
        "blt noargs",
        """\
        blt
        """,
        [
            "line 1: Command 'blt' expects exactly three space-separated arguments (reg reg imm_or_lab), got [''] instead."
        ],
    ),
    (
        "ble one-arg",
        """\
        ble r3
        """,
        [
            "line 1: Command 'ble' expects exactly three space-separated arguments (reg reg imm_or_lab), got ['r3'] instead."
        ],
    ),
    (
        "bgt reg imm",
        """\
        bgt r4 1234
        """,
        [
            "line 1: Command 'bgt' expects exactly three space-separated arguments (reg reg imm_or_lab), got ['r4', '1234'] instead."
        ],
    ),
    (
        "bgt reg imm imm",
        """\
        bgt r4 1234 42
        """,
        [
            "line 1: Cannot parse register for second argument to bgt: Expected register (beginning with 'r'), instead got '1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "bge imm reg imm",
        """\
        bge 1234 r5 42
        """,
        [
            "line 1: Cannot parse register for first argument to bge: Expected register (beginning with 'r'), instead got '1234'. Try something like 'r0' instead."
        ],
    ),
    (
        "beq comma-arg",
        """\
        beq r3, r5 42
        """,
        [
            "line 1: Cannot parse register for first argument to beq: Expected register with numeric index, instead got 'r3,'. Try something like 'r0' instead."
        ],
    ),
    (
        "bne four-arg",
        """\
        bne r3 r4 r5 r6
        """,
        [
            "line 1: Cannot parse immediate for third argument to bne: Expected integer number, instead got 'r5 r6'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for third argument to bne must start with a '_' and contain at least two characters, found name 'r5 r6' instead",
        ],
    ),
    (
        "branch lts comma",
        """\
        blts r5 r6, 5
        """,
        [
            "line 1: Cannot parse register for second argument to blts: Expected register with numeric index, instead got 'r6,'. Try something like 'r0' instead."
        ],
    ),
    (
        "branch gts too large",
        """\
        bgts r5 r6 130
        """,
        [
            "line 1: Command 'bgts' can only branch by offsets in [-128, 129], but not by 130. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
        ],
    ),
    (
        "branch les too negative",
        """\
        bles r10 r9 -129
        """,
        [
            "line 1: Command 'bles' can only branch by offsets in [-128, 129], but not by -129. Try using 'j' instead, which supports larger jumps, or an 'lb*' pseudo-instruction."
        ],
    ),
    (
        "branch ges single arg",
        """\
        bges r10
        """,
        [
            "line 1: Command 'bges' expects exactly three space-separated arguments (reg reg imm_or_lab), got ['r10'] instead."
        ],
    ),
    (
        "branch ges to reg",
        """\
        bges r10 r5 r1
        """,
        [
            "line 1: Cannot parse immediate for third argument to bges: Expected integer number, instead got 'r1'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for third argument to bges must start with a '_' and contain at least two characters, found name 'r1' instead",
        ],
    ),
    (
        "branch bne by 0",
        """\
        bne r10 r11 0
        """,
        [
            "line 1: Command 'bne' cannot encode an infinite loop (offset 0). Try using 'j reg' instead."
        ],
    ),
    (
        "branch bne by 1",
        """\
        bne r10 r11 1
        """,
        [
            "line 1: Command 'bne' cannot encode the nop-branch (offset 1). Try using 'nop' instead."
        ],
    ),
    (
        "senseless pseudo-instruction 'gtz'",
        """\
        gtz r10
        """,
        [
            "line 1: Refusing hypothetical 'gtz' pseudo-instruction, because there is no unsigned"
            " integer less than zero. Consider 'gtsz' for signed comparison, or 'nez' to check for"
            " inequality with zero.",
        ],
    ),
    (
        "senseless pseudo-instruction 'gez'",
        """\
        gez r10
        """,
        [
            "line 1: Command 'gez' not found. Close matches: gesz, ge, bgesz",
        ],
    ),
    (
        "senseless pseudo-instruction 'ltz'",
        """\
        ltz r10
        """,
        [
            "line 1: Command 'ltz' not found. Close matches: ltsz, lt, bltsz",
        ],
    ),
    (
        "senseless pseudo-instruction 'lez'",
        """\
        lez r10
        """,
        [
            "line 1: Refusing hypothetical 'lez' pseudo-instruction, because there is no unsigned"
            " integer less than zero. Consider 'lesz' for signed comparison, or 'eqz' to check for"
            " equality with zero.",
        ],
    ),
    (
        "senseless pseudo-instruction 'bltz'",
        """\
        bltz r10, +42
        """,
        [
            "line 1: Command 'bltz' not found. Close matches: bltsz, blt, lbltsz",
        ],
    ),
    (
        "senseless pseudo-instruction 'blez'",
        """\
        blez r10, +42
        """,
        [
            "line 1: Command 'blez' not found. Close matches: blesz, lez, ble",
        ],
    ),
    (
        "senseless pseudo-instruction 'bgtz'",
        """\
        bgtz r10, +42
        """,
        [
            "line 1: Command 'bgtz' not found. Close matches: bgtsz, gtz, bgt",
        ],
    ),
    (
        "senseless pseudo-instruction 'bgez'",
        """\
        bgez r10, +42
        """,
        [
            "line 1: Command 'bgez' not found. Close matches: bgesz, bge, lbgesz",
        ],
    ),
    (
        "longbranch to forward positive label, too short",
        """\
        lb r0 _destination
        .offset 0x5
        .label _destination
        """,
        [
            "line 1: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
            "line 1: Pseudo-instruction 'lb (to _destination +0 = by +3)' supports jumps in the range [-2048, 2049], but was used for just a short offset of 3. Try using the non-long version, which uses fewer instructions.",
            "line 3: When label _destination was defined.",
        ],
    ),
    (
        "longbranch to backward negative label, too short",
        """\
        .label _destination
        .offset 0x5
        lb r0 _destination
        """,
        [
            "line 3: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
            "line 3: Pseudo-instruction 'lb (to _destination +0 = by -7)' supports jumps in the range [-2048, 2049], but was used for just a short offset of -7. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch to positive immediate, too short",
        """\
        lb r0 +10
        """,
        [
            "line 1: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
            "line 1: Pseudo-instruction 'lb' supports jumps in the range [-2048, 2049], but was used for just a short offset of 10. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch to negative immediate, too short",
        """\
        lb r0 -10
        """,
        [
            "line 1: Command 'lb' inverts the condition register, and ends up needing three instructions. Consider using a combined longbranch-compare instead (e.g. lbles).",
            "line 1: Pseudo-instruction 'lb' supports jumps in the range [-2048, 2049], but was used for just a short offset of -10. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition tworeg, no-arg",
        """\
        lbeq
        """,
        [
            "line 1: Command 'lbeq' expects exactly three space-separated register arguments, got [''] instead.",
        ],
    ),
    (
        "longbranch condition tworeg, one-arg",
        """\
        lbne r1
        """,
        [
            "line 1: Command 'lbne' expects exactly three space-separated register arguments, got ['r1'] instead.",
        ],
    ),
    (
        "longbranch condition tworeg, two-arg",
        """\
        lbne r1 r2
        """,
        [
            "line 1: Command 'lbne' expects exactly three space-separated register arguments, got ['r1', 'r2'] instead.",
        ],
    ),
    (
        "longbranch condition tworeg, reg-reg-reg",
        """\
        lblt r1 r2 r3
        """,
        [
            "line 1: Cannot parse immediate for third argument to lblt: Expected integer number, instead got 'r3'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for third argument to lblt must start with a '_' and contain at least two characters, found name 'r3' instead",
        ],
    ),
    (
        "longbranch condition tworeg, reg-imm-imm",
        """\
        lble r1 2 3
        """,
        [
            "line 1: Cannot parse register for second argument to lble: Expected register (beginning with 'r'), instead got '2'. Try something like 'r0' instead.",
        ],
    ),
    (
        "longbranch condition tworeg, too short imm pos",
        """\
        lbgt r1 r2 +3
        """,
        [
            "line 1: Pseudo-instruction 'lbgt' supports jumps in the range [-2048, 2049], but was used for just a short offset of 3. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition tworeg, too short imm neg",
        """\
        lbge r1 r2 -3
        """,
        [
            "line 1: Pseudo-instruction 'lbge' supports jumps in the range [-2048, 2049], but was used for just a short offset of -3. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition tworeg, too short label forward neg",
        """\
        .offset 10
        lblts r1 r2 _destination
        .offset 2
        .label _destination
        """,
        [
            "line 2: Pseudo-instruction 'lblts (to _destination +0 = by -10)' supports jumps in the range [-2048, 2049], but was used for just a short offset of -10. Try using the non-long version, which uses fewer instructions.",
            "line 4: When label _destination was defined.",
        ],
    ),
    (
        "longbranch condition tworeg, too short label backward pos",
        """\
        .offset 10
        .label _destination
        .offset 2
        lbles r1 r2 _destination
        """,
        [
            "line 4: Pseudo-instruction 'lbles (to _destination +0 = by +6)' supports jumps in the range [-2048, 2049], but was used for just a short offset of 6. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition zero, no-arg",
        """\
        lbeqz
        """,
        [
            "line 1: Command 'lbeqz' expects exactly two space-separated register arguments, got [''] instead.",
        ],
    ),
    (
        "longbranch condition zero, one-arg",
        """\
        lbnez r1
        """,
        [
            "line 1: Command 'lbnez' expects exactly two space-separated register arguments, got ['r1'] instead.",
        ],
    ),
    (
        "longbranch condition zero, reg-reg",
        """\
        lbgtsz r1 r2
        """,
        [
            "line 1: Cannot parse immediate for second argument to lbgtsz: Expected integer number, instead got 'r2'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for second argument to lbgtsz must start with a '_' and contain at least two characters, found name 'r2' instead",
        ],
    ),
    (
        "longbranch condition zero, three arg",
        """\
        lbltsz r1 r2 r3
        """,
        [
            "line 1: Cannot parse immediate for second argument to lbltsz: Expected integer number, instead got 'r2 r3'. Try something like '42', '0xABCD', or '-0x123' instead.",
            "line 1: Label name for second argument to lbltsz must start with a '_' and contain at least two characters, found name 'r2 r3' instead",
        ],
    ),
    (
        "longbranch condition zero, imm-imm",
        """\
        lblesz 1 2
        """,
        [
            "line 1: Cannot parse register for first argument to lblesz: Expected register (beginning with 'r'), instead got '1'. Try something like 'r0' instead.",
        ],
    ),
    (
        "longbranch condition zero, too short imm pos",
        """\
        lbgtsz r1 +3
        """,
        [
            "line 1: Pseudo-instruction 'lbgtsz' supports jumps in the range [-2048, 2049], but was used for just a short offset of 3. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition zero, too short imm neg",
        """\
        lbgesz r1 -3
        """,
        [
            "line 1: Pseudo-instruction 'lbgesz' supports jumps in the range [-2048, 2049], but was used for just a short offset of -3. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "longbranch condition zero, too short label forward neg",
        """\
        .offset 10
        lbltsz r1 _destination
        .offset 2
        .label _destination
        """,
        [
            "line 2: Pseudo-instruction 'lbltsz (to _destination +0 = by -10)' supports jumps in the range [-2048, 2049], but was used for just a short offset of -10. Try using the non-long version, which uses fewer instructions.",
            "line 4: When label _destination was defined.",
        ],
    ),
    (
        "longbranch condition zero, too short label backward pos",
        """\
        .offset 10
        .label _destination
        .offset 2
        lblesz r1 _destination
        """,
        [
            "line 4: Pseudo-instruction 'lblesz (to _destination +0 = by +6)' supports jumps in the range [-2048, 2049], but was used for just a short offset of 6. Try using the non-long version, which uses fewer instructions.",
        ],
    ),
    (
        "jump register high, comma",
        """\
        jhi r0, +0x0000
        """,
        [
            "line 1: Cannot parse register for first argument to jhi: Expected register with numeric index, instead got 'r0,'. Try something like 'r0' instead."
        ],
    ),
    (
        "jump register high, one-arg",
        """\
        jhi r0
        """,
        [
            "line 1: Command 'jhi' expects exactly two space-separated arguments, got ['r0'] instead.",
        ],
    ),
    (
        "jump register high, no-arg",
        """\
        jhi
        """,
        [
            "line 1: Command 'jhi' expects exactly two space-separated arguments, got [''] instead.",
        ],
    ),
    (
        "jump register high, three-arg",
        """\
        jhi r0 +0x0000 123
        """,
        [
            "line 1: Command 'jhi' expects exactly two space-separated arguments, got ['r0', '+0x0000', '123'] instead."
        ],
    ),
    (
        "jump register high, first not a register",
        """\
        jhi 123 +0x0000
        """,
        [
            "line 1: Cannot parse register for first argument to jhi: Expected register (beginning with 'r'), instead got '123'. Try something like 'r0' instead."
        ],
    ),
    (
        "jump register high, offset not aligned",
        """\
        jhi r0 +0x0001
        """,
        [
            "line 1: Offset for jhi must be multiple of 256 in interval [0x0000, 0xFF00], got 0x0001 instead."
        ],
    ),
    (
        "jump register high, negative",
        """\
        jhi r0 -256
        """,
        [
            "line 1: Command 'jhi' requires an offset in [0x0000, 0xFF00], got 0x-100 instead."
        ],
    ),
    (
        "jump register high, strong negative",
        """\
        jhi r0 -4096
        """,
        [
            "line 1: Command 'jhi' requires an offset in [0x0000, 0xFF00], got 0x-1000 instead."
        ],
    ),
    (
        "jump register high, too positive",
        """\
        jhi r0 65536
        """,
        [
            "line 1: Immediate value 65536 (hex: +10000) in second argument to jhi is out of bounds [-0x8000, 0xFFFF]"
        ],
    ),
    (
        "load address, no-arg",
        """\
        la
        """,
        [
            "line 1: Command 'la' expects exactly two comma-separated arguments, got [''] instead.",
        ],
    ),
    (
        "load address, no-comma",
        """\
        .label _foo
        la r5 _foo
        """,
        [
            "line 2: Command 'la' expects exactly two comma-separated arguments, got ['r5 _foo'] instead.",
        ],
    ),
    (
        "load address, one-arg",
        """\
        .label _foo
        la r5
        """,
        [
            "line 2: Command 'la' expects exactly two comma-separated arguments, got ['r5'] instead.",
        ],
    ),
    (
        "load address, three-arg",
        """\
        .label _foo
        la r5, _foo, 123
        """,
        [
            "line 2: Command 'la' expects exactly two comma-separated arguments, got ['r5', '_foo', '123'] instead.",
        ],
    ),
    (
        "load address, first not a register",
        """\
        .label _foo
        la 4, _foo
        """,
        [
            "line 2: Cannot parse register for first argument to la: Expected register (beginning with 'r'), instead got '4'. Try something like 'r0' instead.",
        ],
    ),
    (
        "load address, second not a label (but imm)",
        """\
        la r4, 123
        """,
        [
            "line 1: Label name for second argument to la must start with a '_' and contain at least two characters, found name '123' instead",
        ],
    ),
    (
        "load address, second not a label (but reg)",
        """\
        la r4, r8
        """,
        [
            "line 1: Label name for second argument to la must start with a '_' and contain at least two characters, found name 'r8' instead",
        ],
    ),
    (
        "load address, non-existent",
        """\
        la r3, _nonexistent_lol
        """,
        [
            "line 2: Found end of asm text, but some forward references are unresolved: line 1 at offset 0 references label _nonexistent_lol",
            # FIXME: Shouldn't suggest labels if there are none.
            "line 2: Did you mean any of these defined labels? []",
        ],
    ),
    (
        "load address backward, out-of-range middle",
        """\
        .offset 0x1234
        .label _foo
        .offset 0
        la r11, _foo
        """,
        [
            "line 4: Command 'la' can only load offsets in [-128, 127], but not 0x1234 (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
        ],
    ),
    (
        "load address backward, barely too positive",
        """\
        .offset 0x0080
        .label _foo
        .offset 0
        la r11, _foo
        """,
        [
            "line 4: Command 'la' can only load offsets in [-128, 127], but not 0x0080 (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
        ],
    ),
    (
        "load address backward, barely too negative",
        """\
        .offset 0xFF7F
        .label _foo
        .offset 0
        la r11, _foo
        """,
        [
            "line 4: Command 'la' can only load offsets in [-128, 127], but not 0xFF7F (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
        ],
    ),
    (
        "load address forward, out-of-range middle",
        """\
        la r11, _foo
        .offset 0x1234
        .label _foo
        """,
        [
            "line 1: Command 'la' can only load offsets in [-128, 127], but not 0x1234 (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
            "line 3: When label _foo was defined.",
        ],
    ),
    (
        "load address forward, barely too positive",
        """\
        la r11, _foo
        .offset 0x0080
        .label _foo
        """,
        [
            "line 1: Command 'la' can only load offsets in [-128, 127], but not 0x0080 (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
            "line 3: When label _foo was defined.",
        ],
    ),
    (
        "load address forward, barely too negative",
        """\
        la r11, _foo
        .offset 0xFF7F
        .label _foo
        """,
        [
            "line 1: Command 'la' can only load offsets in [-128, 127], but not 0xFF7F (_foo). Try using moving the label (and changing associated code), or switch to an 'l*' pseudo-instruction.",
            "line 3: When label _foo was defined.",
        ],
    ),
    (
        "load address backward, misspell",
        """\
        .label  _hello_world
        la r11, _hello_wordl
        """,
        [
            "line 3: Found end of asm text, but some forward references are unresolved: line 2 at offset 0 references label _hello_wordl",
            "line 3: Did you mean any of these defined labels? ['_hello_world']",
            "line 3: Unused label(s), try using them in dead code, or commenting them out: '_hello_world' (line 1, offset 0)",
        ],
    ),
    (
        "long load address, no-arg",
        """\
        lla
        """,
        [
            "line 1: Command 'lla' expects exactly two comma-separated arguments, got [''] instead.",
        ],
    ),
    (
        "long load address, no-comma",
        """\
        .label _foo
        lla r5 _foo
        """,
        [
            "line 2: Command 'lla' expects exactly two comma-separated arguments, got ['r5 _foo'] instead.",
        ],
    ),
    (
        "long load address, one-arg",
        """\
        .label _foo
        lla r5
        """,
        [
            "line 2: Command 'lla' expects exactly two comma-separated arguments, got ['r5'] instead.",
        ],
    ),
    (
        "long load address, three-arg",
        """\
        .label _foo
        lla r5, _foo, 123
        """,
        [
            "line 2: Command 'lla' expects exactly two comma-separated arguments, got ['r5', '_foo', '123'] instead.",
        ],
    ),
    (
        "long load address, first not a register",
        """\
        .label _foo
        lla 4, _foo
        """,
        [
            "line 2: Cannot parse register for first argument to lla: Expected register (beginning with 'r'), instead got '4'. Try something like 'r0' instead.",
        ],
    ),
    (
        "long load address, second not a label (but imm)",
        """\
        lla r4, 123
        """,
        [
            "line 1: Label name for second argument to lla must start with a '_' and contain at least two characters, found name '123' instead",
        ],
    ),
    (
        "long load address, second not a label (but reg)",
        """\
        lla r4, r8
        """,
        [
            "line 1: Label name for second argument to lla must start with a '_' and contain at least two characters, found name 'r8' instead",
        ],
    ),
    (
        "long load address, non-existent",
        """\
        lla r3, _nonexistent_lol
        """,
        [
            "line 2: Found end of asm text, but some forward references are unresolved: line 1 at offset 0 references label _nonexistent_lol",
            # FIXME: Shouldn't suggest labels if there are none.
            "line 2: Did you mean any of these defined labels? []",
        ],
    ),
    (
        "long load address backward, misspell",
        """\
        .label  _hello_world
        lla r11, _hello_wordl
        """,
        [
            "line 3: Found end of asm text, but some forward references are unresolved: line 2 at offset 0 references label _hello_wordl",
            "line 3: Did you mean any of these defined labels? ['_hello_world']",
            "line 3: Unused label(s), try using them in dead code, or commenting them out: '_hello_world' (line 1, offset 0)",
        ],
    ),
]

TESTS_INSTRUCTIONS_RS = [
    (
        "from test_time_jump",
        """\
        j r0 +0x0005
        nop
        nop
        nop
        nop
        time
        """,
        "B005 5F00 5F00 5F00 5F00 102D",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6},
    ),
    (
        "from test_time_long",
        """\
        lw r7, 0xFFAB
        decr r7
        b r7 -0x1
        time
        yield
        """,
        "37AB 5877 9780 102D 102A",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5},
    ),
    (
        "from test_time_very_long",
        """\
        lw r7, 0xB505 # executed 1 time
        mov r1, r7 # executed 1 time
        .label _outer_loop
        mov r2, r7 # executed 0xB505 times
        .label _inner_loop
        decr r2 # executed 0xB505 * 0xB505 times
        b r2 _inner_loop # (offset is -0x1) # executed 0xB505 * 0xB505 times
        decr r1 # executed 0xB505 times
        b r1 _outer_loop # (offset is -0x4) # executed 0xB505 times
        time # executed 0 times or 1 time, depending on how you look at it
        yield # executed 1 times
        """,
        "3705 47B5 5F71 5F72 5822 9280 5811 9183 102D 102A",
        [],
        {0: 1, 1: 1, 2: 2, 3: 4, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 11},
    ),
    (
        "from test_store_data_doc",
        """\
        lw r2, 0x1234
        lw r5, 0x5678
        sw r2, r5
        """,
        "3234 4212 3578 4556 2025",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3},
    ),
    (
        "from test_store_data_simple",
        """\
        lw r2, 0x0045
        lw r5, 0x0067
        sw r2, r5
        """,
        "3245 3567 2025",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_load_data_doc",
        """\
        lw r2, 0x1234
        lw r5, r2
        """,
        "3234 4212 2125",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_load_data_simple",
        """\
        lw r2, 0x0005
        lw r5, r2
        """,
        "3205 2125",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_load_instruction_doc",
        """\
        lw r2, 0x1234
        lwi r5, r2
        """,
        "3234 4212 2225",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_load_instruction_simple",
        """\
        lw r2, 0x0005
        lwi r5, r2
        """,
        "3205 2225",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_load_imm_high_doc_setup",
        """\
        lw r10, 0x1234
        """,
        "3A34 4A12",
        [],
        {0: 1, 1: 1},
    ),
    (
        "from test_load_imm_high_doc",
        """\
        lw r10, 0x1234
        lhi r10, 0x5600
        """,
        "3A34 4A12 4A56",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_load_imm_high_simple",
        """\
        lhi r5, 0xAB00
        """,
        "45AB",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_doc1",
        """\
        lhi r7, 0x1200
        j r7 +0x0034
        """,
        "4712 B734",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_doc2",
        """\
        lw r7, 0x1234
        j r7 -0x0001
        """,
        "3734 4712 B7FF",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_jump_register_simple",
        """\
        j r0 +0x0042
        """,
        "B042",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_overflow",
        """\
        lw r7, 0xFFFF
        j r7 +0x0010
        """,
        "37FF B710",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_underflow",
        """\
        j r0 -0x0080
        """,
        "B080",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_extreme_positive_imm",
        """\
        j r0 +0x7F
        """,
        "B07F",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_extreme_negative_imm",
        """\
        j r0 -0x80
        """,
        "B080",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_extreme_positive",
        """\
        lw r7, 0xFFFF
        j r7 +0x7F
        """,
        "37FF B77F",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_extreme_positive_nowrap",
        """\
        lw r7, 0x7FFF
        j r7 +0x7F
        """,
        "37FF 477F B77F",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_jump_register_extreme_negative",
        """\
        lw r7, 0xFFFF
        j r7 -0x80
        """,
        "37FF B780",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_extreme_negative_signedish",
        """\
        lw r7, 0x8000
        j r7 -0x80
        """,
        # The example doesn't use 3700, but the assembler shouldn't make such optimizations.
        "3700 4780 B780",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_jump_register_high_doc1",
        """\
        lw r10, 0x0034
        jhi r10 +0x1200
        """,
        "3A34 CA12",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_high_doc2",
        """\
        lw r0, 0xA5A5
        jhi r0 +0xF000
        """,
        "30A5 40A5 C0F0",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_jump_register_high_simple",
        """\
        jhi r0 +0x4200
        """,
        "C042",
        [],
        {0: 1},
    ),
    (
        "from test_jump_register_high_extreme",
        """\
        lw r7, 0xFFFF
        jhi r7 +0xFF00
        """,
        "37FF C7FF",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_jump_register_high_zero",
        """\
        jhi r0 +0x0000
        """,
        "C000",
        [],
        {0: 1},
    ),
    (
        "from test_program_counter_wraps",
        """\
        lw r7, 0xFFFF
        j r7 +0x0000
        .offset 0xFFFF
        lw r4, 0x0012
        """,
        "37FF B700 " + ("0000 " * (65536 - 3)) + "3412",
        ["line 4: segment pointer overflow, now at 0x0000 (non-fatal)"],
        {0: 1, 1: 2, 0xFFFF: 4},
    ),
    (
        "from test_jump_imm_doc1",
        """\
        lhi r3, 0x5000
        j r3 +0x0000
        .offset 0x5000
        j +0x125
        """,
        "4350 B300 " + ("0000 " * (0x5000 - 2)) + "A123",
        [],
        {0: 1, 1: 2, 0x5000: 4},
    ),
    (
        "from test_jump_imm_doc2",
        """\
        lhi r3, 0x1200
        j r3 +0x0034
        .offset 0x1234
        j -0x1
        """,
        "4312 B334 " + ("0000 " * (0x1234 - 2)) + "A800",
        [],
        {0: 1, 1: 2, 0x1234: 4},
    ),
    (
        "from test_jump_immediate_overflow",
        """\
        lw r3, 0xFF00
        j r3 +0x0000
        .offset 0xFF00
        j +0x202
        """,
        # The example doesn't use 3300, but the assembler shouldn't make such optimizations.
        "3300 43FF B300 " + ("0000 " * (0xFF00 - 3)) + "A200" + (" 0000" * 0xFF),
        [],
        {0: 1, 1: 1, 2: 2, 0xFF00: 4},
    ),
    (
        "from test_jump_immediate_underflow",
        """\
        j -0x031
        """,
        "A830",
        [],
        {0: 1},
    ),
    (
        "from test_jump_immediate_extreme_positive",
        """\
        j +0x801
        """,
        "A7FF",
        [],
        {0: 1},
    ),
    (
        "from test_jump_immediate_extreme_negative",
        """\
        j -0x800
        """,
        "AFFF",
        [],
        {0: 1},
    ),
    (
        "from test_branch_doc1",
        """\
        lw r3, 0x0001
        lhi r7, 0x1200
        j r7 +0x0034
        .offset 0x1234
        b r3 -0x1
        """,
        "3301 4712 B734 " + ("0000 " * (0x1234 - 3)) + "9380",
        [],
        {0: 1, 1: 2, 2: 3, 0x1234: 5},
    ),
    (
        "from test_branch_doc2",
        """\
        b r5 -0x1
        """,
        "9580",
        [],
        {0: 1},
    ),
    (
        "from test_compare_doc",
        """\
        lw r3, 0x0005
        lw r4, 0x0007
        ne r3 r4
        """,
        "3305 3407 8A34",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_unary_doc1",
        """\
        lw r5, 0x1234
        not r6, r5
        """,
        "3534 4512 5A56",
        [],
        {0: 1, 1: 1, 2: 2},
    ),
    (
        "from test_unary_doc2",
        """\
        lw r3, 41
        incr r3
        """,
        "3329 5933",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_unary_rnd_inclusive",
        """\
        lw r1, 5
        rnd r2, r1
        le r2 r1
        ge r2 r0
        """,
        "3105 5E12 8C21 8620",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "from test_unary_rnd_extreme",
        """\
        lw r1, 0xFFFF
        rnd r2, r1
        eq r2 r1
        eq r2 r0
        """,
        "31FF 5E12 8421 8420",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "from test_binary_doc",
        """\
        lw r5, 5
        lw r6, 7
        mul r5 r6
        """,
        "3505 3607 6256",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_fibonacci",
        """\
        lw r0, 24
        lw r1, 1
        .label _start
        add r1 r2
        decr r0
        sw r0, r2
        add r2 r1
        decr r0
        sw r0, r1
        b r0 _start # (offset is -0x6)
        yield
        """,
        "3018 3101 6012 5800 2002 6021 5800 2001 9085 102A",
        [],
        {0: 1, 1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 11},
    ),
    (
        "from test_rnd_(not_)exec",
        """\
        lw r0, 7
        nop
        rnd r2, r0
        """,
        "3007 5F00 5E02",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
]


TESTS_CONNECT4_RS = [
    (
        "from test_two_random 202503",
        """\
        lw r0, 1
        rnd r1
        yield
        j -3
        """,
        "3001 5E11 102A A802",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "from test_connect4 202503 player two",
        """\
        lw r0, 0x0001
        yield
        j -2
        """,
        "3001 102A A801",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_connect4 202503 player one",
        """\
        lw r0, 0
        yield
        j -2
        """,
        "3000 102A A801",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_two_illegal_column 202503",
        """\
        lw r0, 0
        yield
        """,
        "3000 102A",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_timeout 202503",
        """\
        lw r0, 1
        j r0 +0x0000
        """,
        "3001 B000",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_full_column 202503",
        """\
        lw r0, 0
        yield
        j -2
        """,
        "3000 102A A801",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_determine_answer_multiple",
        """\
        lw r0, 0x7A
        lw r1, 0x23
        sw r0, r1
        yield
        lw r0, 0x3B
        sw r1, r0
        yield
        """,
        "307A 3123 2001 102A 303B 2010 102A",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7},
    ),
    (
        "from test_determine_answer",
        """\
        lw r0, 0x1337
        lw r7, 0xABCD
        sw r7, r7
        yield
        """,
        "3037 4013 37CD 47AB 2077 102A",
        [],
        {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4},
    ),
    (
        "from test_board_full player one",
        """\
        lw r1, 0xFF89 # Address of total number of moves made by this player.
        lw r1, r1
        lw r0, 7
        modu r1 r0
        yield
        """,
        "3189 2111 3007 6610 102A",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5},
    ),
    (
        "from test_board_full player two",
        """\
        lw r1, 0xFF89
        lw r1, r1
        b r1 _move_nonzero # (offset is +0x3)
        # .label _move_zero # On move 0, play in column 3.
        lw r0, 3
        yield
        .label _move_nonzero
        lw r0, 18
        ge r1 r0
        b r0 _move_late # (offset is +0x2)
        # .label _move_early # On moves 1-17, play in column (n - 1) % 7.
        decr r1
        # j _move_late # Surprise optimization: This is a noop, this time!
        .label _move_late # On moves 18-20, play in column n % 7.
        lw r0, 7
        modu r1 r0
        yield
        """,
        "3189 2111 9101 3003 102A 3012 8610 9000 5811 3007 6610 102A",
        [],
        -1,  # Mapping too long, not interesting
    ),
    (
        "from test_determine_answer_random",
        """\
        lw r0, 6
        rnd r1, r0
        yield
        """,
        "3006 5E01 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_two_random",
        """\
        rnd r1
        lw r0, 1
        yield
        """,
        "5E11 3001 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
]

TESTS_TEST_DRIVER_RS = [
    (
        "from test_illegal_instruction_late 202506",
        """\
        nop
        debug
        nop
        ill
        """,
        "5F00 102C 5F00 FFFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4},
    ),
    (
        "from test_illegal_yield 202506",
        """\
        lw r0, 0x42
        yield
        """,
        "3042 102A",
        [],
        {0: 1, 1: 2},
    ),
    (
        "from test_illegal_yield_ffff 202506",
        """\
        lw r0, 0xFFFF
        nop
        yield
        """,
        "30FF 5F00 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_check_environment_id 202506",
        """\
        lw r0, 0xFFFF
        lw r1, 0xFFFE
        lw r2, 0xFFFD
        lw r8, r0
        lw r9, r1
        lw r10, r2
        ill
        """,
        "30FF 31FE 32FD 2108 2119 212A FFFF",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7},
    ),
    (
        "from test_done_zero_invalid 202506",
        """\
        lw r0, 2  # "done"
        lw r1, 0  # num tests
        yield
        """,
        "3002 3100 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_done_zero_valid 202506",
        """\
        lw r0, 2  # "done"
        lw r1, 0  # num tests
        lw r8, 0x0000
        lw r9, 0x650D
        sw r8, r9
        lw r8, 0x0001
        lw r9, 0x4585
        sw r8, r9
        yield
        """,
        "3002 3100 3800 390D 4965 2089 3801 3985 4945 2089 102A",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 4, 5: 5, 6: 6, 7: 7, 8: 7, 9: 8, 10: 9},
    ),
    (
        "from test_done_negone_invalid 202506",
        """\
        lw r0, 2  # "done"
        lw r1, -1  # num tests
        yield
        """,
        "3002 31FF 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_done_negtwo_invalid 202506",
        """\
        lw r0, 2  # "done"
        lw r1, -2  # num tests
        yield
        """,
        "3002 31FE 102A",
        [],
        {0: 1, 1: 2, 2: 3},
    ),
    (
        "from test_done_negtwo_valid 202506",
        """\
        lw r0, 2  # "done"
        lw r1, -2  # num tests
        lw r8, 0xFFFE
        lw r9, 0x650D
        sw r8, r9
        lw r8, 0xFFFF
        lw r9, 0x4585
        sw r8, r9
        yield
        """,
        "3002 31FE 38FE 390D 4965 2089 38FF 3985 4945 2089 102A",
        [],
        {0: 1, 1: 2, 2: 3, 3: 4, 4: 4, 5: 5, 6: 6, 7: 7, 8: 7, 9: 8, 10: 9},
    ),
    (
        "from test_done_multi_prio_1_illegal 202506",
        """\
        lw r0, 2  # "done"
        lw r1, 5  # num tests
        lw r8, 0x0000
        lw r9, 1  # "pass"
        sw r8, r9
        incr r8
        lw r9, 2  # "fail"
        sw r8, r9
        incr r8
        lw r9, 3  # "fatal error"
        sw r8, r9
        incr r8
        lw r9, 4  # "skip"
        sw r8, r9
        incr r8
        lw r9, 5  # "illegal"
        sw r8, r9
        incr r8
        lw r9, 0x650D
        sw r8, r9
        incr r8
        lw r9, 0x4585
        sw r8, r9
        yield
        """,
        "3002 3105 3800 3901 2089 5988 3902 2089 5988 3903 2089 5988 3904 2089 5988 3905 2089 5988 390D 4965 2089 5988 3985 4945 2089 102A",
        [],
        -1,  # Not interesting enough
    ),
]


def uphex(bytes_or_none):
    if bytes_or_none is None:
        return None
    return bytes_or_none.hex().upper()


class AsmTests(unittest.TestCase):
    def test_empty(self):
        empty_result = asm.CompilationResult(b"\x00" * asm.SEGMENT_LENGTH, [], dict())
        self.assertEqual(empty_result, asm.compile_assembly(""))
        self.assertEqual(empty_result, asm.compile_assembly("\n"))

    def check_testsuite_consistency(self, suite, suite_name):
        name_counter = Counter(entry[0] for entry in suite)
        for name, count in name_counter.items():
            with self.subTest(t=suite_name, name=name):
                self.assertEqual(count, 1)

    def test_testsuite_names(self):
        self.check_testsuite_consistency(ASM_TESTS, "ASM_TESTS")
        self.check_testsuite_consistency(NEGATIVE_TESTS, "NEGATIVE_TESTS")
        self.check_testsuite_consistency(TESTS_INSTRUCTIONS_RS, "TESTS_INSTRUCTIONS_RS")
        self.check_testsuite_consistency(TESTS_CONNECT4_RS, "TESTS_CONNECT4_RS")
        self.check_testsuite_consistency(TESTS_TEST_DRIVER_RS, "TESTS_TEST_DRIVER_RS")

    def assert_assembly(
        self, asm_text, expected_segment, expected_error_log, expected_mapping
    ):
        actual_result = asm.compile_assembly(asm_text)
        self.assertEqual(expected_error_log, actual_result.error_log)
        self.assertEqual(uphex(expected_segment), uphex(actual_result.segment))
        if isinstance(expected_mapping, int) and expected_mapping == -1:
            self.assertIsNotNone(actual_result.mapping)
        else:
            self.assertEqual(expected_mapping, actual_result.mapping)

    def parse_and_extend_hex(self, code_prefix_hex):
        segment = bytearray.fromhex(code_prefix_hex)
        self.assertTrue(len(segment) <= asm.SEGMENT_LENGTH)
        if len(segment) > asm.SEGMENT_LENGTH // 2:
            # If a very long sequence is specified, it's probably supposed to be the entire program.
            self.assertEqual(len(segment), asm.SEGMENT_LENGTH)
        else:
            self.assertEqual(len(segment) % 2, 0)
            padding = b"\x00" * (asm.SEGMENT_LENGTH - len(segment))
            segment.extend(padding)
        return segment

    def run_positive_hardcoded(self, testsuite):
        for i, data_tuple in enumerate(testsuite):
            (
                name,
                asm_text,
                code_prefix_hex,
                expected_error_log,
                expected_mapping,
            ) = data_tuple
            with self.subTest(i=i, name=name):
                expected_segment = self.parse_and_extend_hex(code_prefix_hex)
                self.assert_assembly(
                    asm_text, expected_segment, expected_error_log, expected_mapping
                )

    def test_hardcoded(self):
        self.run_positive_hardcoded(ASM_TESTS)

    def test_negative(self):
        for i, data_tuple in enumerate(NEGATIVE_TESTS):
            name, asm_text, expected_error_log = data_tuple
            with self.subTest(i=i, name=name):
                self.assert_assembly(asm_text, None, expected_error_log, None)

    def test_from_instructions_rs(self):
        self.run_positive_hardcoded(TESTS_INSTRUCTIONS_RS)

    def test_from_connect4_rs(self):
        self.run_positive_hardcoded(TESTS_CONNECT4_RS)

    def test_from_test_driver_rs(self):
        self.run_positive_hardcoded(TESTS_TEST_DRIVER_RS)


if __name__ == "__main__":
    unittest.main()
