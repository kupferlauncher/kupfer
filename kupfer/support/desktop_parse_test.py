#! /usr/bin/env python3
# pylint: disable=protected-access
"""
This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
import unittest

from . import desktop_parse


class TestUnescape(unittest.TestCase):
    def test1(self):
        self.assertEqual(
            desktop_parse._unescape(r'"This \\$ \\\\ \s\\\\"'),
            '"This \\$ \\\\  \\\\"',
        )
        self.assertEqual(desktop_parse._unescape(r"\t\s\\\\"), "\t \\\\")
