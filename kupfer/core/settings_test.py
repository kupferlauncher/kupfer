# Distributed under terms of the GPLv3 license.

"""

"""
import unittest
from dataclasses import dataclass, field
import typing as ty

from kupfer.core import settings as S

import icecream

icecream.install()


class TestConfBase(unittest.TestCase):
    def test_defaults(self):
        @dataclass
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
            list2: list[ty.Any] = field(default_factory=lambda: [1, "abc"])
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        self.assertEqual(tconf.get_default_value("integer"), 191)
        self.assertEqual(tconf.get_default_value("string"), "abc")
        self.assertEqual(tconf.get_default_value("list1"), [1, 2, 3, 4])
        self.assertEqual(tconf.get_default_value("list2"), [1, "abc"])
        self.assertEqual(tconf.get_default_value("boolean1"), False)
        self.assertEqual(tconf.get_default_value("boolean2"), True)

    def test_dict_not_default1(self):
        @dataclass
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
            list2: list[ty.Any] = field(default_factory=lambda: [1, "abc"])
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        res = tconf.asdict_non_default()
        self.assertEqual(res, {})

    def test_dict_not_default2(self):
        @dataclass
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
            list2: list[ty.Any] = field(default_factory=lambda: [1, "abc"])
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = 19
        tconf.list2 = [2, "abc"]
        res = tconf.asdict_non_default()
        self.assertEqual(res, {"integer": 19, "list2": [2, "abc"]})

    def test_dict_not_default3(self):
        @dataclass
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
            list2: list[ty.Any] = field(default_factory=lambda: [1, "abc"])
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = 1
        tconf.string = "123"
        tconf.list1 = []
        tconf.list2 = [2]
        tconf.boolean1 = True
        tconf.boolean2 = False
        res = tconf.asdict_non_default()
        self.assertEqual(
            res,
            {
                "integer": 1,
                "string": "123",
                "list1": [],
                "list2": [2],
                "boolean1": True,
                "boolean2": False,
            },
        )

    def test_conversion(self):
        @dataclass
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = field(default_factory=lambda: [1, 2, 3, 4])
            list2: list[ty.Any] = field(default_factory=lambda: [1, "abc"])
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = "123"
        self.assertEqual(tconf.integer, 123)

        tconf.boolean1 = "yes"
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "no"
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "True"
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "False"
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "true"
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "false"
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "1"
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "0"
        self.assertEqual(tconf.boolean1, False)

        tconf.list1 = "[1,2,3,99]"
        self.assertEqual(tconf.list1, [1, 2, 3, 99])
