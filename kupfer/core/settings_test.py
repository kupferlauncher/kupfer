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

    def test_dict_not_default_dicts(self):
        class TConf(S.ConfBase):
            d: dict[int, dict[int, int]] = {1: {11: 11, 12: 12}, 2: {21: 21}}

        tconf = TConf()
        tconf.d = {1: {11: 111, 12: 12}, 2: {21: 21, 22: 22}}
        res = tconf.asdict_non_default()
        self.assertEqual(
            res,
            {
                "d": {
                    1: {11: 111},
                    2: {22: 22},
                }
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

    def test_asdict(self):
        class TSubConf(S.ConfBase):
            integer: int = 134
            string: str = "qwe"

        class TConf(S.ConfBase):
            boolean1: bool = False
            boolean2: bool = True
            sub: TSubConf

        tconf = TConf()
        odict = tconf.asdict()
        self.assertEqual(odict["boolean1"], False)
        self.assertEqual(odict["boolean2"], True)
        self.assertEqual(odict["sub"]["integer"], 134)
        self.assertEqual(odict["sub"]["string"], "qwe")

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
            dictionary: dict[int, int] = {1: 1, 2: 2}

        tconf = TConf()

        self.assertEqual(tconf.sub.get_default_value("integer1"), 134)
        self.assertEqual(tconf.sub.get_default_value("integer2"), 234)
        self.assertEqual(tconf.sub.get_default_value("string1"), "qwe")
        self.assertEqual(tconf.sub.get_default_value("string2"), "asd")
        self.assertEqual(tconf.get_default_value("boolean1"), False)
        self.assertEqual(tconf.get_default_value("boolean2"), True)
        self.assertEqual(tconf.get_default_value("dictionary"), {1: 1, 2: 2})

        # this should not change anything now
        tconf.save_as_defaults()

        self.assertEqual(tconf.sub.get_default_value("integer1"), 134)
        self.assertEqual(tconf.sub.get_default_value("integer2"), 234)
        self.assertEqual(tconf.sub.get_default_value("string1"), "qwe")
        self.assertEqual(tconf.sub.get_default_value("string2"), "asd")
        self.assertEqual(tconf.get_default_value("boolean1"), False)
        self.assertEqual(tconf.get_default_value("boolean2"), True)
        # is dict copied?
        self.assertTrue(tconf._defaults["dictionary"] is not tconf.dictionary)
        self.assertEqual(tconf.get_default_value("dictionary"), {1: 1, 2: 2})

        tconf.sub.integer1 = 456
        tconf.sub.string1 = "zxc"
        tconf.boolean1 = True
        tconf.dictionary[3] = 3

        # is defaults not changed?
        self.assertTrue(3 not in tconf._defaults["dictionary"])

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
            dictionary: dict[int, ty.Any] = {1: 1, 2: 2, 3: {1: 3}}

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

        tconf.dictionary[3][1] = 2
        tconf.reset_value("dictionary")
        self.assertEqual(tconf.dictionary, {1: 1, 2: 2, 3: {1: 3}})

        tconf.dictionary = {2: 3, 4: 12}
        tconf.reset_value("dictionary")
        self.assertEqual(tconf.dictionary, {1: 1, 2: 2, 3: {1: 3}})


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

[DeepDirectories]
direct = dir1;dir2;dir3
 """

        parser = configparser.RawConfigParser()
        parser.read_string(data)

        c = S.Configuration()
        c.keybindings["comma_trick"] = "<Control>comma"

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

        self.assertEqual(c.deep_directories.direct, ["dir1", "dir2", "dir3"])

    def test_load_defaults(self):
        """Test if loading configuration for plugins correct overwrite default
        values."""
        data = """
# qsicon is empty, so this configuration should be cleared
[plugin_qsicons]

# this should be merged
[plugin_favorites]
kupfer_enabled = True
test = 1

# and this partial overwritten
[plugin_core]
kupfer_hidden = False
kupfer_enabled = True
 """

        parser = configparser.RawConfigParser()
        parser.read_string(data)

        c = S.Configuration()
        S._fill_configuration_from_parser(parser, c)

        self.assertEqual(c.kupfer.keybinding, "<Ctrl>space")
        self.assertEqual(len(c.plugins["qsicons"]), 0)
        self.assertEqual(c.plugins["favorites"]["kupfer_enabled"], "True")
        self.assertEqual(c.plugins["favorites"]["test"], "1")
        self.assertEqual(c.plugins["core"]["kupfer_enabled"], "True")
        self.assertEqual(c.plugins["core"]["kupfer_hidden"], "False")


class TestConfiguration(unittest.TestCase):
    def test_get_plugin_defaule_value(self):
        c = S.Configuration()
        c.plugins["core"] = S.ConfPlugin(
            "core", {"kupfer_enabled": "True", "kupfer_hidden": "True"}
        )

        # for test use core plugin
        plugc = c.plugins["core"]
        self.assertTrue(plugc)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", str)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", int)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", bool)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", bool)

        plugc["test_existing"] = "qwe"
        self.assertEqual(plugc.get_value("test_existing", str), "qwe")
        plugc["test_existing"] = "321"
        self.assertEqual(plugc.get_value("test_existing", int), 321)
        plugc["test_existing"] = False  # type: ignore
        self.assertEqual(plugc.get_value("test_existing", bool), False)
        plugc["test_existing"] = True  # type: ignore
        self.assertEqual(plugc.get_value("test_existing", bool), True)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", str)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", int)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", bool)

        with self.assertRaises(KeyError):
            plugc.get_value("test_not_existing", bool)


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

    def test_convert_func(self):
        def vc1(value: str) -> S.PlugConfigValue:
            return f"-{value}-"

        self.assertEqual(S._convert(None, vc1), None)
        self.assertEqual(S._convert("abc", vc1), "-abc-")
        self.assertEqual(S._convert("", vc1), "--")


class TestFill(unittest.TestCase):
    def test_fill_from_parser(self):
        c = S.Configuration()
        data = """
[Appearance]
ellipsize_mode = 321
icon_small_size = 3333

[Directories]
direct = /test;/test2/ttt

[plugin_aria2]
aria2_token = token
aria2_url = http://address:6800/jsonrpc
kupfer_enabled = True

[plugin_apt_tools]
installation_method = gksu -- apt-get install --yes
kupfer_enabled = False
"""
        parser = configparser.RawConfigParser()
        parser.read_string(data)
        S._fill_configuration_from_parser(parser, c)

        self.assertEqual(c.appearance.ellipsize_mode, 321)
        self.assertEqual(c.appearance.icon_small_size, 3333)
        self.assertEqual(c.directories.direct, ["/test", "/test2/ttt"])

        aria = c.plugins["aria2"]
        self.assertEqual(aria["aria2_token"], "token")
        self.assertEqual(aria["aria2_url"], "http://address:6800/jsonrpc")
        self.assertEqual(aria["kupfer_enabled"], "True")

        apt = c.plugins["apt_tools"]
        self.assertEqual(
            apt["installation_method"], "gksu -- apt-get install --yes"
        )
        self.assertEqual(apt["kupfer_enabled"], "False")

    def test_fill_parser(self):
        # test using default values for simplify
        c = S.Configuration()
        c.appearance.icon_large_size = 128
        c.appearance.ellipsize_mode = 0
        c.directories.direct = ["~/", "~/Desktop;USER_DIRECTORY_DESKTOP"]
        c.plugins["applications"] = S.ConfPlugin(
            "applications", {"kupfer_enabled": True}
        )
        c.plugins["core"] = S.ConfPlugin(
            "core", {"kupfer_enabled": True, "kupfer_hidden": True}
        )
        confmap = c.asdict()

        parser = configparser.RawConfigParser()
        S._fill_parser_from_config(parser, confmap)

        # all values are strings
        self.assertEqual(parser["Appearance"]["icon_large_size"], "128")
        self.assertEqual(parser["Appearance"]["ellipsize_mode"], "0")
        # lists are strings separated by SettingsController.sep
        self.assertEqual(
            parser["Directories"]["direct"],
            "~/;~/Desktop;USER_DIRECTORY_DESKTOP",
        )
        # plugins should be on toplevel
        self.assertEqual(
            parser["plugin_applications"]["kupfer_enabled"], "True"
        )
        self.assertEqual(parser["plugin_core"]["kupfer_enabled"], "True")
        self.assertEqual(parser["plugin_core"]["kupfer_hidden"], "True")


class TestConvertNames(unittest.TestCase):
    def test_name_to_configparser(self):
        self.assertEqual(S._name_to_configparser("kupfer"), "Kupfer")
        self.assertEqual(S._name_to_configparser("deep_dirs"), "DeepDirs")

    def test_name_from_configparser(self):
        self.assertEqual(S._name_from_configparser("Kupfer"), "kupfer")
        self.assertEqual(S._name_from_configparser("DeepDirs"), "deep_dirs")
