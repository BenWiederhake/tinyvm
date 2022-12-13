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
]


class AsmTests(unittest.TestCase):
    def test_empty(self):
        asm.ERROR_OUTPUT = False
        self.assertEqual(b"\x00" * asm.SEGMENT_LENGTH, asm.compile_to_segment(""))
        self.assertEqual(b"\x00" * asm.SEGMENT_LENGTH, asm.compile_to_segment("\n"))

    def test_testsuite_names(self):
        nameCounter = Counter(name for name, _, _ in ASM_TESTS)
        for name, count in nameCounter.items():
            with self.subTest(name=name):
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


if __name__ == "__main__":
    unittest.main()
