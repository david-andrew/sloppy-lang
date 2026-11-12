#!/usr/bin/env python3
"""Regression tests for doccheck's extraction and fail-closed checking."""
import unittest

import doccheck as d


class Extraction(unittest.TestCase):
    def test_indented_fences(self):
        source = 'prose\n  ```gdscript\n  print("hello")\n  ```\n\n```gdscript\nprint(2)\n```\n'
        blocks = [d.normalize(m[1]) for m in d.FENCE.finditer(source)]
        self.assertEqual(blocks, ['print("hello")\n', 'print(2)\n'])

    def test_comments_stop_at_prose(self):
        source = '#   a = 1\n#\n#   print(a)\n# This prose must not be consumed.\nf = (): pass\n'
        self.assertEqual([m[0] for m in d.COMMENTS.finditer(source)], ['#   a = 1\n#\n#   print(a)'])

    def test_duplicate_context_is_stable(self):
        self.assertEqual(d.normalize('  print(1)\n  '), d.normalize('print(1)\n'))

    def test_statement_holes(self):
        self.assertEqual(d.statement_holes('...\nif ok: ... # body\n'), 'pass\nif ok: pass # body\n')

    def test_literals_and_spreads_are_untouched(self):
        code = 'print("literal: ... # text")\ns = """\n...\n"""\nf(xs...)\n# ...\n'
        self.assertEqual(d.statement_holes(code), code)

    def test_expression_holes_fail_closed(self):
        self.assertEqual(d.statement_holes('sprite(...)\ndraw = (): ... state ...\n'), 'sprite(...)\ndraw = (): ... state ...\n')

    def test_portable_library_context(self):
        code = d.prepare("print(1)", {"uses": ["std/snapshot"]})
        self.assertIn(str(d.ROOT / "lib/std/snapshot.jo"), code)

    def test_typed_function_context(self):
        code = d.prepare('result = read_file(path)?\n', {'before': 'path = "test.txt"\n', 'function': ' -> void | FileError'})
        self.assertIn('doccheck_example = () -> void | FileError:\n    result = read_file(path)?', code)


class Diagnostics(unittest.TestCase):
    def test_unknown_api_is_failure(self):
        self.assertFalse(d.accepted(1, "x:1:1: error: unknown function 'old_api'\n"))

    def test_nondiagnostic_failure_is_failure(self):
        self.assertFalse(d.accepted(2, ''))

    def test_negative_example_requires_exact_diagnostic(self):
        self.assertTrue(d.accepted(1, 'x:1:1: error: expected failure\n', 'expected failure'))
        self.assertFalse(d.accepted(0, '', 'expected failure'))
        self.assertFalse(d.accepted(1, 'x:1:1: error: another failure\n', 'expected failure'))

    def test_extra_errors_and_crashes_are_failures(self):
        errors = 'x:1:1: error: expected failure\nx:2:1: error: unknown function\n'
        self.assertFalse(d.accepted(1, errors, 'expected failure'))
        self.assertFalse(d.accepted(1, 'panic:\nx:1:1: error: expected failure\n', 'expected failure'))


if __name__ == '__main__':
    unittest.main()
