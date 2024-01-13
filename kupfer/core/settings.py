"""This module implement `SettingsController` and classes related to Kupfer
configuration.

Configuration (in new model) is stored in `Configuration` class
(SettingsController.config).

Each field of `Configuration` class should be either or simple objects (int,
floats, string, tuple, list, dict, set) or object that extend `ConfBase` class.

`ConfBase` provide some "magic" like:
1. keep "default" values for each field; default values are declared in class or
   can be get from current values by `save_as_defaults`.
2. notify SettingsController on changes
3. on assign - convert value to declared for each field type - each field must
   be declared.
4. return recursive object as dict.


For persist or load configuration `SettingsController` use adapter; for now
only adapter for `configparser` is implemented.

TODO: tuples; better handling for plugins configuration

"""


from __future__ import annotations

import configparser
import locale
import os
import typing as ty
import ast
import inspect
from contextlib import suppress
import copy

from gi.repository import GLib, GObject, Pango

from kupfer import config
from kupfer.support import pretty, scheduler, datatools

__all__ = (
    "SettingsController",
    "get_settings_controller",
    "is_known_terminal_executable",
    "get_configured_terminal",
)

# Function used to validate/accept alternatives
AltValidator = ty.Callable[[dict[str, ty.Any]], bool]

# TODO: move to StrEnum (py3.11+)
KUPFER_ENABLED: ty.Final = "kupfer_enabled"
KUPFER_HIDDEN: ty.Final = "kupfer_hidden"


def _get_annotations(clazz: type) -> dict[str, ty.Any]:
    """Get type annotations for given class `clazz`. Support python <3.10."""
    # for python 3.10+
    if hasattr(inspect, "get_annotations"):
        return inspect.get_annotations(clazz, eval_str=True)  # type: ignore

    # python <3.10; simplified version - this is sufficient for our classes
    ann: dict[str, ty.Any]
    ann = clazz.__dict__.get("__annotations__", None)
    assert ann

    for key, val in ann.items():
        if isinstance(val, str):
            ann[key] = eval(val)

    return ann


class ConfBase:
    """Base class for all configuration.
    On create copy all dict, list and other values from class defaults."""

    def __init__(self):
        # store evaluated annotations
        self._annotations = _get_annotations(self.__class__)
        assert self._annotations, "class should have annotated fields"

        # defaults
        self._defaults: dict[str, ty.Any] = {}

        clazz = self.__class__
        for key, field_type in self._annotations.items():
            value = None

            if field_type in (str, int, tuple, bool, float):
                # this types are safe to copy
                value = getattr(clazz, key)
            elif str(field_type).startswith("list"):
                # copy list or create empty
                if dval := getattr(clazz, key, None):
                    value = copy.deepcopy(dval)
                else:
                    value = []

            elif str(field_type).startswith("dict"):
                # copy dict or create empty
                if dval := getattr(clazz, key, None):
                    value = copy.deepcopy(dval)
                else:
                    value = {}

            else:
                # for other types create object
                value = field_type()

            super().__setattr__(key, value)

    def __setattr__(self, name, value):
        if name[0] == "_":
            # attributes that name starts with _ are set as is
            pass

        elif field_type := self._annotations.get(name):
            # conversion only from strings
            if isinstance(value, str) and field_type != str:
                value = _convert(value, field_type)

            # do nothing when value is not changed
            current_val = getattr(self, name, None)
            if current_val == value:
                pretty.print_debug("skip", self, name, value)
                return

            with suppress(AttributeError):
                # notify about value changed
                if SettingsController._inst:
                    SettingsController._inst.mark_updated()

            pretty.print_debug("set", self, name, value)

        else:
            pretty.print_error("unknown parameter", name, value)
            return

        super().__setattr__(name, value)

    def save_as_defaults(self):
        """Save current values as default. For objects call `save_as_defaults`
        method if exists. For sets/dicts/lists - make copy."""
        fields = set(self._annotations.keys())
        for key, val in self.__dict__.items():
            if key not in fields:
                continue

            if val is None:
                continue

            if hasattr(val, "save_as_defaults"):
                val.save_as_defaults()
                continue

            if isinstance(val, (dict, set, list)):
                val = copy.deepcopy(val)

            self._defaults[key] = val

    def get_default_value(self, field_name: str) -> ty.Any:
        """Get default value for `field_name`."""
        if field_name in self._defaults:
            return self._defaults[field_name]

        return getattr(self.__class__, field_name, None)

    def asdict_non_default(self) -> dict[str, ty.Any]:
        """Get dict of attributes that differ from default."""
        res = {}

        fields = set(self._annotations.keys())
        for key, val in self.__dict__.items():
            if key not in fields:
                continue

            if val and hasattr(val, "asdict_non_default"):
                res[key] = val.asdict_non_default()
                continue

            default = self.get_default_value(key)
            # ship unchanged values
            if default == val:
                continue

            # for dict compare current value against defaults and return
            # only changes.
            if isinstance(val, dict) and default is not None:
                assert isinstance(default, dict)
                val = dict(datatools.compare_dicts(val, default))

            res[key] = val

        return res

    def asdict(self) -> dict[str, ty.Any]:
        """Return content as dict."""
        return {
            key: (val.asdict() if hasattr(val, "asdict") else val)
            for key, val in self.__dict__.items()
        }

    def reset_value(self, field_name: str) -> None:
        """Reset value in `field_name` to default value."""
        setattr(self, field_name, self.get_default_value(field_name))


class ConfKupfer(ConfBase):
    """Basic Kupfer configuration."""

    # Kupfer keybinding as string
    keybinding: str = "<Ctrl>space"
    # Kupfer alternate keybinding as string
    magickeybinding: str = ""
    showstatusicon: bool = True
    showstatusicon_ai: bool = False
    usecommandkeys: bool = True
    action_accelerator_modifer: str = "ctrl"


class ConfAppearance(ConfBase):
    """Appearance configuration."""

    icon_large_size: int = 128
    icon_small_size: int = 24
    list_height: int = 250
    ellipsize_mode: int = 0


class ConfDirectories(ConfBase):
    """Directories configuration."""

    # it safe to create list here because on instantiate there are be copied
    direct: list[str] = ["~/", "~/Desktop", "USER_DIRECTORY_DESKTOP"]
    catalog: list[str] = []


class ConfDeepDirectories(ConfBase):
    """Deep directories configuration."""

    direct: list[str]
    catalog: list[str]
    depth: int = 2


ConfPluginValueType = ty.Union[int, float, str, bool, None]


class ConfPlugin(dict[str, ConfPluginValueType]):
    """Plugin configuration - extended dict.
    All values are simple types, list/tuples/objects are stored as strings.
    """

    def __init__(
        self, plugin_name: str, *argv: ty.Any, **kwarg: ty.Any
    ) -> None:
        self.plugin_name = plugin_name
        super().__init__(*argv, **kwarg)

    def set_enabled(self, enabled: bool) -> None:
        self[KUPFER_ENABLED] = enabled

    def get_value(
        self,
        key: str,
        value_type: ty.Any = str,
        default: PlugConfigValue | None = None,
    ) -> PlugConfigValue | None:
        if key not in self:
            return default

        val = self[key]

        if isinstance(value_type, type) and issubclass(
            value_type, ExtendedSetting
        ):
            val_obj: ExtendedSetting = value_type()
            val_obj.load(self.plugin_name, key, val)
            return val_obj

        if val is None:
            return None

        value = ty.cast(PlugConfigValue, _convert(val, value_type, default))
        return value

    def set_value(
        self,
        key: str,
        value: PlugConfigValue,
        value_type: ty.Any = str,
    ) -> bool:
        """Try set @key for plugin names @plugin, coerce to @value_type first."""

        value_repr: int | str | float | bool | None

        if value is None or isinstance(value, (str, float, int, bool)):
            value_repr = value
        elif isinstance(value, ExtendedSetting):
            value_repr = value.save(self.plugin_name, key)
        elif value_type is list:
            value_repr = str(value)

        self[key] = value_repr
        return True


def _default_keybindings() -> dict[str, str]:
    return {
        "activate": "<Alt>a",
        "comma_trick": "<Control>comma",
        "compose_action": "<Control>Return",
        "erase_affinity_for_first_pane": "",
        "mark_as_default": "",
        "reset_all": "<Control>r",
        "select_quit": "<Control>q",
        "select_selected_file": "",
        "select_selected_text": "<Control>g",
        "show_help": "F1",
        "show_preferences": "<Control>semicolon",
        "switch_to_source": "",
        "toggle_text_mode_quick": "<Control>period",
    }


def _default_tools() -> dict[str, str]:
    return {
        "terminal": "kupfer.plugin.core.gnome-terminal",
        "editor": "kupfer.plugin.core.sys-editor",
        "icon_renderer": "kupfer.plugin.core.gtk",
    }


def _default_plugins() -> dict[str, ConfPlugin]:
    res = {}

    def set_enabled(name: str, val: bool) -> None:
        res[name] = ConfPlugin(name, {KUPFER_ENABLED: val})

    set_enabled("applications", True)
    set_enabled("archivemanager", True)
    set_enabled("calculator", True)
    set_enabled("clipboard", True)
    set_enabled("commands", True)
    set_enabled("dictionary", True)
    set_enabled("documents", True)
    set_enabled("favorites", True)
    set_enabled("qsicons", True)
    set_enabled("show_text", True)
    set_enabled("triggers", True)
    set_enabled("trash", True)
    set_enabled("urlactions", True)
    set_enabled("volumes", True)
    set_enabled("wikipedia", True)

    set_enabled("fileactions", False)
    set_enabled("session_gnome", False)
    set_enabled("session_xfce", False)
    set_enabled("screen", False)
    set_enabled("tracker1", False)
    set_enabled("windows", False)

    set_enabled("core", True)
    res["core"][KUPFER_HIDDEN] = True

    return res


class Configuration(ConfBase):
    kupfer: ConfKupfer
    appearance: ConfAppearance
    directories: ConfDirectories
    deep_directories: ConfDeepDirectories

    keybindings: dict[str, ty.Any] = _default_keybindings()
    tools: dict[str, ty.Any] = _default_tools()
    plugins: dict[str, ConfPlugin] = _default_plugins()


@ty.runtime_checkable
class ExtendedSetting(ty.Protocol):
    """Protocol that define non-simple configuration option"""

    def load(
        self,
        plugin_id: str,
        key: str,
        config_value: str | float | int | bool | None,
    ) -> None:
        """load value for @plugin_id and @key, @config_value is value
        stored in regular Kupfer config for plugin/key"""

    def save(self, plugin_id: str, key: str) -> str:
        """Save value for @plugin_id and @key.
        @Return value that should be stored in Kupfer config for
        plugin/key (string)"""


PlugConfigValue = ty.Union[str, bool, int, float, list[ty.Any], ExtendedSetting]


# pylint: disable=too-few-public-methods
@ty.runtime_checkable
class ValueConverter(ty.Protocol):
    """Protocol that represent callable used to convert value stored
    in config file (as str) into required value (int, float, etc).
    """

    def __call__(self, value: str, default: ty.Any) -> PlugConfigValue:
        ...


# pylint: disable=too-many-return-statements
def _convert(value: ty.Any, dst_type: ty.Any, default: ty.Any = None) -> ty.Any:
    """Convert `value` to `dst_type`."""
    if value is None:
        return None

    # if value is in right type - return it
    if isinstance(dst_type, type) and isinstance(value, dst_type):
        return value

    if dst_type in ("int", int):
        try:
            return int(value)
        except ValueError:
            return default

    if dst_type in ("bool", bool):
        return _strbool(value)

    if dst_type in ("float", float):
        try:
            return float(value)
        except ValueError:
            return default

    if dst_type in ("str", str):
        return str(value)

    if dst_type in ("tuple", tuple):
        raise NotImplementedError()

    if dst_type in ("list", list):
        return _strlist(value)

    # complex types
    dst_types = (
        dst_type.__name__ if isinstance(dst_type, type) else str(dst_type)
    )
    if dst_types.startswith("list["):
        # support only simple types inside list
        value = _strlist(value)
        items_type = dst_types[5:-1]
        return [_convert(item, items_type) for item in value]

    if isinstance(dst_type, ValueConverter):
        if isinstance(value, str):
            with suppress(NameError):
                return dst_type(value, default=default)

    with suppress(TypeError):
        return dst_type(value)

    raise ValueError(f"not supported dst_type: `{dst_type}` for {value!r}")


def _strbool(value: ty.Any, default: bool = False) -> bool:
    """Coerce bool from string value or bool"""
    if isinstance(value, bool):
        return value

    value = str(value).lower()
    if value in ("no", "false"):
        return False

    if value in ("yes", "true", "1"):
        return True

    return default


def _strlist(value: str, default: list[ty.Any] | None = None) -> list[ty.Any]:
    """Parse string into list using ast literal_eval.

    literal_eval handle only 'safe' data, so should work fine.
    """
    if not value:
        return []

    if (value[0] == "[" and value[-1] == "]") or (
        value[0] == "(" and value[-1] == ")"
    ):
        try:
            val = ast.literal_eval(value)
            if isinstance(val, list):
                return val
            if isinstance(val, tuple):
                return list(val)

            raise ValueError(f"invalid type: {val!r}")
        except (TypeError, SyntaxError, MemoryError, RecursionError) as err:
            raise ValueError(f"evaluate {value!r} error") from err

    return list(
        filter(None, map(str.strip, value.split(SettingsController.sep)))
    )


def _override_encoding(name: str) -> str | None:
    """Return a new encoding name if we want to override it, else return None.

    This is used to “upgrade” ascii to UTF-8 since the latter is a superset.
    """
    if name.lower() in ("ascii", "ANSI_X3.4-1968".lower()):
        return "UTF-8"

    return None


def _name_from_configparser(name: str) -> str:
    """Convert `CamelCase` to `name_with_underscopes`.
    It's not perfect (work well only for alfa-characters.
    """
    return "".join(
        f"_{c.lower()}" if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" else c
        for c in name
    ).lstrip("_")


def _fill_configuration_from_parser(
    parser: configparser.RawConfigParser,
    conf: Configuration,
) -> None:
    """Put values from `parser` to `confmap` using `defaults` as schema."""
    for secname in parser.sections():
        section = parser[secname]
        if secname.startswith("plugin_"):
            psecname = secname[7:].lower()
            sobj = conf.plugins.get(psecname)
            if sobj is None:
                sobj = conf.plugins[psecname] = ConfPlugin(psecname)
        else:
            name = _name_from_configparser(secname)
            sobj = getattr(conf, name, None)
            if sobj is None:
                pretty.print_error("unknown secname", secname)
                continue

        if isinstance(sobj, dict):
            # empty section clear current (also default) settings
            if len(section):
                sobj.update(section.items())
            else:
                sobj.clear()

        elif isinstance(sobj, ConfBase):
            for key, val in section.items():
                setattr(sobj, key.lower(), val)
        else:
            pretty.print_error("unknown secname", secname, sobj)


def _name_to_configparser(name: str) -> str:
    """Convert `name_with_underscopes` to `CamelCase`."""
    return "".join(p.capitalize() for p in name.split("_"))


def _fill_parser_from_config(
    parser: configparser.RawConfigParser, conf: dict[str, dict[str, ty.Any]]
) -> None:
    """Put content of `config` dict into `parser`."""
    for secname, section in sorted(conf.items()):
        if secname == "plugins":
            continue

        # for backward compatibility capitalize first character in section
        # name; section are case-sensitive.
        secname = _name_to_configparser(secname)

        if not parser.has_section(secname):
            parser.add_section(secname)

        for key, value in sorted(section.items()):
            if isinstance(value, (tuple, list)):
                value = SettingsController.sep.join(value)
            else:
                value = str(value)

            parser.set(secname, key, value)

    # save plugins
    plugins = conf["plugins"]
    for secname, section in sorted(plugins.items()):
        secname = f"plugin_{secname}"
        if not parser.has_section(secname):
            parser.add_section(secname)

        for key, value in sorted(section.items()):
            if isinstance(value, (tuple, list)):
                value = SettingsController.sep.join(value)
            else:
                value = str(value)

            parser.set(secname, key, value)


class ConfigparserAdapter(pretty.OutputMixin):
    config_filename = "kupfer.cfg"
    defaults_filename = "defaults.cfg"

    def __init__(self):
        self.encoding = _override_encoding(locale.getpreferredencoding())
        self.output_debug("Using", self.encoding)

    def save(self, conf: Configuration) -> None:
        self.output_info("Saving config")
        config_path = config.save_config_file(self.config_filename)
        if not config_path:
            self.output_info("Unable to save settings, can't find config dir")
            return

        parser = configparser.RawConfigParser()
        confmap = conf.asdict_non_default()
        _fill_parser_from_config(parser, confmap)
        ## Write to tmp then rename over for it to be atomic
        temp_config_path = f"{config_path}.{os.getpid()}"
        with open(temp_config_path, "w", encoding="UTF_8") as out:
            parser.write(out)

        os.rename(temp_config_path, config_path)

    def _load_from_file(
        self, config_file: str
    ) -> configparser.RawConfigParser | None:
        parser = configparser.RawConfigParser()
        try:
            parser.read(config_file, encoding=self.encoding)
            return parser
        except OSError as exc:
            self.output_error(
                f"Error reading configuration file {config_file}: {exc}"
            )
        except UnicodeDecodeError as exc:
            self.output_error(
                f"Error reading configuration file {config_file}: {exc}"
            )

        return None

    def load(self, read_config: bool = True) -> Configuration:
        """Read cascading config files: default -> then config
        (in all XDG_CONFIG_DIRS)."""

        # Set up defaults - declared in classes
        confmap = Configuration()
        # load defaults from file
        if config_file := config.get_config_file(self.defaults_filename):
            if parser := self._load_from_file(config_file):
                _fill_configuration_from_parser(parser, confmap)

        confmap.save_as_defaults()

        # load user config file
        if config_file := config.get_config_file(self.config_filename):
            if parser := self._load_from_file(config_file):
                _fill_configuration_from_parser(parser, confmap)

        return confmap


def _source_config_repr(obj: ty.Any) -> str:
    name = type(obj).__name__
    return "".join((c if c.isalnum() else "_") for c in name)


# pylint: disable=too-many-public-methods
class SettingsController(GObject.GObject, pretty.OutputMixin):  # type: ignore
    __gtype_name__ = "SettingsController"
    sep = ";"
    _inst: SettingsController | None = None

    @classmethod
    def instance(cls) -> SettingsController:
        """SettingsController is singleton; instance return one, global
        instance."""
        if cls._inst is None:
            cls._inst = SettingsController()

        assert cls._inst
        return cls._inst

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self._adapter = ConfigparserAdapter()
        self.config = self._adapter.load()
        self._save_timer = scheduler.Timer(True)

        self._alternatives: dict[str, ty.Any] = {}
        self._alternative_validators: dict[str, AltValidator | None] = {}

        self.output_debug("config", self.config)

    def mark_updated(self):
        if SettingsController._inst is not None:
            self.output_info("mark_updated", SettingsController._inst)
            self._save_timer.set(60, self._save_config)

    def _save_config(self, _scheduler: ty.Any = None) -> None:
        self._adapter.save(self.config)

    def get_plugin_enabled(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is enabled"""
        return ty.cast(
            bool,
            self.get_plugin_config(plugin_id, KUPFER_ENABLED, bool, False),
        )

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> None:
        """Convenience: set if @plugin_id is enabled"""
        self.set_plugin_config(
            plugin_id, KUPFER_ENABLED, enabled, value_type=bool
        )
        self.emit("plugin-enabled-changed", plugin_id, enabled)

    def get_plugin_is_hidden(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is hidden"""
        return ty.cast(
            bool,
            self.get_plugin_config(plugin_id, KUPFER_HIDDEN, bool, False),
        )

    def get_source_is_toplevel(self, plugin_id: str, src: ty.Any) -> bool:
        key = "kupfer_toplevel_" + _source_config_repr(src)
        default = not getattr(src, "source_prefer_sublevel", False)
        return ty.cast(
            bool, self.get_plugin_config(plugin_id, key, bool, default)
        )

    def set_source_is_toplevel(
        self, plugin_id: str, src: ty.Any, value: bool
    ) -> None:
        key = "kupfer_toplevel_" + _source_config_repr(src)
        self.emit("plugin-toplevel-changed", plugin_id, value)
        self.set_plugin_config(plugin_id, key, value, value_type=bool)

    def get_global_keybinding(self, key: str) -> str:
        if key == "keybinding":
            return self.config.kupfer.keybinding

        if key == "magickeybinding":
            return self.config.kupfer.magickeybinding

        raise ValueError("invalid key {key}")

    def set_global_keybinding(self, key: str, val: str) -> None:
        if key == "keybinding":
            self.config.kupfer.keybinding = val
        elif key == "magickeybinding":
            self.config.kupfer.magickeybinding = val

    def get_directories(self, direct: bool = True) -> ty.Iterator[str]:
        """Yield directories to use as directory sources"""
        specialdirs = {
            k: getattr(GLib.UserDirectory, k)
            for k in dir(GLib.UserDirectory)
            if k.startswith("DIRECTORY_")
        }

        def get_special_dir(opt):
            if opt.startswith("USER_"):
                if sdir := specialdirs.get(opt[5:]):
                    return GLib.get_user_special_dir(sdir)

            return None

        cat = (
            self.config.directories.direct
            if direct
            else self.config.directories.catalog
        )
        for direc in cat:
            dpath = get_special_dir(direc)
            yield dpath or os.path.abspath(os.path.expanduser(direc))

    def get_plugin_config(
        self,
        plugin: str,
        key: str,
        value_type: ty.Any = str,
        default: PlugConfigValue | None = None,
    ) -> PlugConfigValue | None:
        """Return setting @key for plugin names @plugin, try to coerce to
        type @value_type.
        Else return @default if does not exist, or can't be coerced
        """
        try:
            plugin_cfg = self.config.plugins[plugin]
        except KeyError:
            return default

        try:
            return plugin_cfg.get_value(key, value_type, default)
        except (ValueError, TypeError) as err:
            self.output_error(f"Error for load value {plugin}.{key}", err)

        return default

    def set_plugin_config(
        self,
        plugin: str,
        key: str,
        value: PlugConfigValue,
        value_type: ty.Any = str,
    ) -> bool:
        """Try set @key for plugin names @plugin, coerce to @value_type first."""
        self.output_debug("set_plugin_config", plugin, key, value)

        plugin_conf = self.config.plugins.get(plugin)
        if plugin_conf is None:
            plugin_conf = self.config.plugins[plugin] = ConfPlugin(plugin)

        plugin_conf.set_value(key, value, value_type)
        section = f"plugin_{plugin}"
        self.emit(
            f"value-changed::{section.lower()}.{key.lower()}",
            section,
            key,
            value,
        )
        self.mark_updated()
        return True

    def reset_keybindings(self) -> None:
        self.config.kupfer.reset_value("keybinding")
        self.config.kupfer.reset_value("magickeybinding")

    def reset_accelerators(self) -> None:
        self.config.keybindings.update(_default_keybindings())

    ## Alternatives section
    ## Provide alternatives for each category
    ## for example the category "terminal"
    def get_valid_alternative_ids(
        self, category_key: str
    ) -> ty.Iterator[tuple[str, str]]:
        """Get a list of (id_, name) tuples for the given @category_key."""
        if category_key not in self._alternative_validators:
            return

        validator = self._alternative_validators[category_key]
        for id_, alternative in self._alternatives[category_key].items():
            if not validator or validator(alternative):
                name = alternative["name"]
                yield (id_, name)

    def get_all_alternatives(self, category_key: str) -> ty.Any:
        return self._alternatives[category_key]

    def get_preferred_alternative(
        self, category_key: str
    ) -> dict[str, ty.Any] | None:
        """Get preferred alternative dict for @category_key."""
        tool_id = self.config.tools.get(category_key)
        alternatives = self._alternatives[category_key]
        if alt := alternatives.get(tool_id):
            assert not alt or isinstance(alt, dict)
            return alt

        self.output_debug("Warning, no configuration for", category_key)
        return next(iter(alternatives.values()), None)

    def update_alternatives(
        self,
        category_key: str,
        alternatives: dict[str, ty.Any],
        validator: AltValidator | None,
    ) -> None:
        self._alternatives[category_key] = alternatives
        self._alternative_validators[category_key] = validator
        self.emit("alternatives-changed::" + category_key, category_key)

    def get_ellipsize_mode(self) -> Pango.EllipsizeMode:
        if self.config.appearance.ellipsize_mode == 1:
            return Pango.EllipsizeMode.END

        return Pango.EllipsizeMode.MIDDLE


# Arguments: Section, Key, Value
# Detailed by 'section.key' in lowercase
GObject.signal_new(
    "value-changed",
    SettingsController,
    GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.DETAILED,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_PYOBJECT),
)

# Arguments: Plugin ID, Value
GObject.signal_new(
    "plugin-enabled-changed",
    SettingsController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_INT),
)

# Arguments: Plugin ID, Value
GObject.signal_new(
    "plugin-toplevel-changed",
    SettingsController,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_INT),
)

# Arguments: Alternative-category
# Detailed by: category key, in lowercase
GObject.signal_new(
    "alternatives-changed",
    SettingsController,
    GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.DETAILED,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING,),
)


# Get SettingsController instance
get_settings_controller = SettingsController.instance


def is_known_terminal_executable(exearg: str) -> bool:
    """Check is `exearg` is know terminal executable"""
    setctl = get_settings_controller()
    for _id, term in setctl.get_all_alternatives("terminal").items():
        if exearg == term["argv"][0]:
            return True

    return False


def get_configured_terminal() -> dict[str, ty.Any] | None:
    """Return the configured Terminal object"""
    setctl = get_settings_controller()
    return setctl.get_preferred_alternative("terminal")
