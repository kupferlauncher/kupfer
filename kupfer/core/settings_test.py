# Distributed under terms of the GPLv3 license.

"""

"""
import unittest
import typing as ty
import configparser

from kupfer.core import settings as S

import icecream

icecream.install()


class TestConfBase(unittest.TestCase):
    def test_defaults(self):
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
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
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        res = tconf.asdict_non_default()
        self.assertEqual(res, {})

    def test_dict_not_default2(self):
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = 19
        tconf.list2 = [2, "abc"]
        res = tconf.asdict_non_default()
        self.assertEqual(res, {"integer": 19, "list2": [2, "abc"]})

    def test_dict_not_default3(self):
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
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
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = "123"  # type: ignore
        self.assertEqual(tconf.integer, 123)

        tconf.boolean1 = "yes"  # type: ignore
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "no"  # type: ignore
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "True"  # type: ignore
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "False"  # type: ignore
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "true"  # type: ignore
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "false"  # type: ignore
        self.assertEqual(tconf.boolean1, False)
        tconf.boolean1 = "1"  # type: ignore
        self.assertEqual(tconf.boolean1, True)
        tconf.boolean1 = "0"  # type: ignore
        self.assertEqual(tconf.boolean1, False)

        tconf.list1 = "[1,2,3,99]"  # type: ignore
        self.assertEqual(tconf.list1, [1, 2, 3, 99])

    def test_embended(self):
        class TSubConf(S.ConfBase):
            integer: int = 134
            string: str = "qwe"

        class TConf(S.ConfBase):
            boolean1: bool = False
            boolean2: bool = True
            sub: TSubConf

        tconf = TConf()
        self.assertTrue(isinstance(tconf.sub, TSubConf))
        self.assertEqual(tconf.sub.integer, 134)

    def test_set(self):
        class TConf(S.ConfBase):
            integer: int = 191
            string: str = "abc"
            list1: list[int] = [1, 2, 3, 4]
            list2: list[ty.Any] = [1, "abc"]
            boolean1: bool = False
            boolean2: bool = True

        tconf = TConf()
        tconf.integer = 1
        tconf.string = "qwe"
        tconf.list1 = [9, 8, 7]
        tconf.list2 = [0, 1, "qwe"]
        tconf.boolean1 = True
        tconf.boolean2 = False
        self.assertEqual(tconf.integer, 1)
        self.assertEqual(tconf.string, "qwe")
        self.assertEqual(tconf.list1, [9, 8, 7])
        self.assertEqual(tconf.list2, [0, 1, "qwe"])
        self.assertEqual(tconf.boolean1, True)
        self.assertEqual(tconf.boolean2, False)

    def test_save_defaults(self):
        class TSubConf(S.ConfBase):
            integer1: int = 134
            integer2: int = 234
            string1: str = "qwe"
            string2: str = "asd"

        class TConf(S.ConfBase):
            boolean1: bool = False
            boolean2: bool = True
            sub: TSubConf

        tconf = TConf()
        tconf.save_as_defaults()

        self.assertEqual(tconf.sub.get_default_value("integer1"), 134)
        self.assertEqual(tconf.sub.get_default_value("integer2"), 234)
        self.assertEqual(tconf.sub.get_default_value("string1"), "qwe")
        self.assertEqual(tconf.sub.get_default_value("string2"), "asd")
        self.assertEqual(tconf.get_default_value("boolean1"), False)
        self.assertEqual(tconf.get_default_value("boolean2"), True)

        tconf.sub.integer1 = 456
        tconf.sub.string1 = "zxc"
        tconf.boolean1 = True

        tconf.save_as_defaults()

        self.assertEqual(tconf.sub.get_default_value("integer1"), 456)
        self.assertEqual(tconf.sub.get_default_value("integer2"), 234)
        self.assertEqual(tconf.sub.get_default_value("string1"), "zxc")
        self.assertEqual(tconf.sub.get_default_value("string2"), "asd")
        self.assertEqual(tconf.get_default_value("boolean1"), True)
        self.assertEqual(tconf.get_default_value("boolean2"), True)

    def test_reset(self):
        class TSubConf(S.ConfBase):
            integer1: int = 134
            integer2: int = 234
            string1: str = "qwe"
            string2: str = "asd"

        tconf = TSubConf()

        tconf.integer1 = 456
        tconf.string1 = "zxc"

        self.assertEqual(tconf.integer1, 456)
        self.assertEqual(tconf.string1, "zxc")

        tconf.reset_value("integer1")
        tconf.reset_value("string1")

        self.assertEqual(tconf.integer1, 134)
        self.assertEqual(tconf.string1, "qwe")

        tconf.integer1 = 4567
        tconf.string1 = "zxcd"

        tconf.save_as_defaults()

        tconf.integer1 = 1
        tconf.string1 = "aaa"

        self.assertEqual(tconf.integer1, 1)
        self.assertEqual(tconf.string1, "aaa")

        tconf.reset_value("integer1")
        tconf.reset_value("string1")

        self.assertEqual(tconf.integer1, 4567)
        self.assertEqual(tconf.string1, "zxcd")


class TestFillConfigurationFromParser(unittest.TestCase):
    def test_load(self):
        data = """
[Kupfer]
keybinding = keybinding123
usecommandkeys = False

[Appearance]
icon_large_size = 1

[keybindings]
keybinding1 = key123
activate = key321

[deepdirectories]
direct = dir1;dir2;dir3
 """

        parser = configparser.RawConfigParser()
        parser.read_string(data)

        c = S.Configuration()
        S._fill_configuration_from_parser(parser, c)

        self.assertEqual(c.kupfer.keybinding, "keybinding123")
        self.assertEqual(c.kupfer.usecommandkeys, False)
        self.assertEqual(c.appearance.icon_large_size, 1)
        # new key
        self.assertEqual(c.keybindings["keybinding1"], "key123")
        # changed
        self.assertEqual(c.keybindings["activate"], "key321")
        # not changed
        self.assertEqual(c.keybindings["comma_trick"], "<Control>comma")

        self.assertEqual(c.deepdirectories.direct, ["dir1", "dir2", "dir3"])


class TestConfiguration(unittest.TestCase):
    def test_create(self):
        c = S.Configuration()
        self.assertTrue(isinstance(c.kupfer, S.ConfKupfer))
        self.assertEqual(c.kupfer.keybinding, "<Ctrl>space")
        self.assertEqual(c.keybindings.get("activate"), "<Alt>a")
        self.assertEqual(
            c.directories.direct, ["~/", "~/Desktop", "USER_DIRECTORY_DESKTOP"]
        )


class TestConvert(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(S._convert(None, str), None)
        self.assertEqual(S._convert("abc", str), "abc")
        self.assertEqual(S._convert("abc", "str"), "abc")

        self.assertEqual(S._convert(123, int), 123)
        self.assertEqual(S._convert(123, "int"), 123)
        self.assertEqual(S._convert("123", "int"), 123)
        self.assertEqual(S._convert("123", int), 123)

        self.assertEqual(S._convert("True", bool), True)
        self.assertEqual(S._convert("1", bool), True)
        self.assertEqual(S._convert("yes", bool), True)
        self.assertEqual(S._convert("false", bool), False)
        self.assertEqual(S._convert("No", bool), False)

        self.assertEqual(S._convert("[1,2,3]", list), [1, 2, 3])

        self.assertEqual(S._convert("[1,2,3]", "list[str]"), ["1", "2", "3"])
