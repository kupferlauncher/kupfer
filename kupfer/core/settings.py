from __future__ import annotations

import configparser
import locale
import os
import typing as ty
import ast
import inspect

from gi.repository import GLib, GObject, Pango

from kupfer import config
from kupfer.support import pretty, scheduler

__all__ = (
    "SettingsController",
    "get_settings_controller",
    "is_known_terminal_executable",
    "get_configured_terminal",
)

AltValidator = ty.Callable[[dict[str, ty.Any]], bool]
Config = dict[str, dict[str, ty.Any]]


class ConfBase:
    """Base class for all configuration.
    On create copy all dict, list and other values from class defaults."""

    def __init__(self):
        self._defaults: dict[str, ty.Any] = {}
        clazz = self.__class__
        ann = inspect.get_annotations(self.__class__, eval_str=True)  # type: ignore
        for key, field_type in ann.items():
            value = None

            if field_type in (str, int, tuple, bool, float):
                # this types are safe to copy
                value = getattr(clazz, key)
            elif str(field_type).startswith("list"):
                # copy list or create empty
                if dval := getattr(clazz, key, None):
                    value = dval.copy()
                else:
                    value = []

            elif str(field_type).startswith("dict"):
                # copy dict or create empty
                if dval := getattr(clazz, key, None):
                    value = dval.copy()
                else:
                    value = {}

            else:
                # for other types create object
                value = field_type()

            super().__setattr__(key, value)

    def __setattr__(self, name, value):
        if field_type := self.__class__.__annotations__.get(name):
            if (
                isinstance(value, str)
                and (field_type is not str and field_type != "str")
                and value is not None
            ):
                if field_type is int or field_type == "int":
                    value = _strint(value)
                elif field_type is bool or field_type == "bool":
                    value = _strbool(value)
                elif str(field_type).startswith("list["):
                    value = _strlist(value)

            # do nothing when value is not changed
            current_val = getattr(self, name, None)
            if current_val == value:
                return

            try:
                # notify about value changed
                if SettingsController._inst:
                    SettingsController._inst.mark_updated()

            except AttributeError:
                pass

        elif name[0] != "_":
            pretty.print_error("unknown parameter", name, value)

        super().__setattr__(name, value)

    def save_as_defaults(self):
        """Save current values as default. For objectc call `save_as_defaults`
        method if exists. For sets/dicts/lists - make copy."""
        fields = set(self.__annotations__.keys())
        for key, val in self.__dict__.items():
            if key not in fields:
                continue

            if val is None:
                continue

            if hasattr(val, "save_as_defaults"):
                val.save_as_defaults()
                continue

            if isinstance(val, (dict, set, list)):
                val = val.copy()

            self._defaults[key] = val

    def get_default_value(self, field_name: str) -> ty.Any:
        """Get default value for `field_name`."""
        if field_name in self._defaults:
            return self._defaults[field_name]

        return getattr(self.__class__, field_name)

    def asdict_non_default(self) -> dict[str, ty.Any]:
        """Get dict of attributes that differ from default. For
        dict only first level is compared."""
        res = {}

        fields = set(self.__annotations__.keys())
        for key, val in self.__dict__.items():
            if key not in fields:
                continue

            if val is None:
                continue

            if hasattr(val, "asdict_non_default"):
                res[key] = val.asdict_non_default()
                continue

            default = self.get_default_value(key)
            # ship unchanged values
            if default == val:
                continue

            if isinstance(val, dict):
                assert isinstance(default, dict)
                # support only 1-level of dict
                res[key] = {
                    dkey: dval
                    for dkey, dval in val.items()
                    if dval != default.get(dkey)
                }

                continue

            res[key] = val

        return res

    def reset_value(self, field_name: str) -> None:
        setattr(self, field_name, self.get_default_value(field_name))


class ConfKupfer(ConfBase):
    # Kupfer keybinding as string
    keybinding: str = "<Ctrl>space"
    # Kupfer alternate keybinding as string
    magickeybinding: str = ""
    showstatusicon: bool = True
    showstatusicon_ai: bool = False
    usecommandkeys: bool = True
    action_accelerator_modifer: str = "ctrl"


class ConfAppearance(ConfBase):
    icon_large_size: int = 128
    icon_small_size: int = 24
    list_height: int = 250
    ellipsize_mode: int = 0


class ConfDirectories(ConfBase):
    # it safe to create list here because on instantiate there are be copied
    direct: list[str] = ["~/", "~/Desktop", "USER_DIRECTORY_DESKTOP"]
    catalog: list[str] = []


class ConfDeepDirectories(ConfBase):
    direct: list[str]
    catalog: list[str]
    depth: int = 2


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


def _default_plugins() -> dict[str, dict[str, ty.Any]]:
    res = {}

    def set_enabled(name: str, val: bool) -> None:
        res[name] = {"kupfer_enabled": val}

    set_enabled("plugin_applications", True)
    set_enabled("plugin_archivemanager", True)
    set_enabled("plugin_calculator", True)
    set_enabled("plugin_clipboard", True)
    set_enabled("plugin_commands", True)
    set_enabled("plugin_dictionary", True)
    set_enabled("plugin_documents", True)
    set_enabled("plugin_favorites", True)
    set_enabled("plugin_qsicons", True)
    set_enabled("plugin_show_text", True)
    set_enabled("plugin_triggers", True)
    set_enabled("plugin_trash", True)
    set_enabled("plugin_urlactions", True)
    set_enabled("plugin_volumes", True)
    set_enabled("plugin_wikipedia", True)

    set_enabled("plugin_fileactions", False)
    set_enabled("plugin_session_gnome", False)
    set_enabled("plugin_session_xfce", False)
    set_enabled("plugin_screen", False)
    set_enabled("plugin_tracker1", False)
    set_enabled("plugin_windows", False)

    set_enabled("plugin_core", True)
    res["plugin_core"]["kupfer_hidden"] = True

    return res


class Configuration(ConfBase):
    kupfer: ConfKupfer
    appearance: ConfAppearance
    directories: ConfDirectories
    deepdirectories: ConfDeepDirectories

    keybindings: dict[str, ty.Any] = _default_keybindings()
    tools: dict[str, ty.Any] = _default_tools()
    plugins: dict[str, dict[str, ty.Any]] = _default_plugins()


@ty.runtime_checkable
class ExtendedSetting(ty.Protocol):
    """Protocol that define non-simple configuration option"""

    def load(
        self, plugin_id: str, key: str, config_value: str | float | int | None
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


# PlugConfigValueType = ty.Union[type[PlugConfigValue], ValueConverter]
PlugConfigValueType = ty.Union[ty.Any, ValueConverter]


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


def _strint(value: ty.Any, default: int = 0) -> int:
    """Coerce bool from string value or bool"""
    try:
        return int(value)
    except ValueError:
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


def _fill_configuration_from_parser(
    parser: configparser.RawConfigParser,
    conf: Configuration,
) -> None:
    """Put values from `parser` to `confmap` using `defaults` as schema."""
    for secname in parser.sections():
        if secname.startswith("plugin_"):
            sobj = conf.plugins.get(secname.lower())
            if sobj is None:
                sobj = conf.plugins[secname.lower()] = {}
        else:
            sobj = getattr(conf, secname.lower(), None)
            if sobj is None:
                pretty.print_error("unknown secname", secname)
                continue

        if isinstance(sobj, dict):
            sobj.update(parser[secname].items())
        elif isinstance(sobj, ConfBase):
            for key, val in parser[secname].items():
                setattr(sobj, key.lower(), val)
        else:
            pretty.print_error("unknown secname", secname, sobj)


def _fill_parser_from_config(
    parser: configparser.RawConfigParser, config: Config
) -> None:
    """Put content of `config` dict into `parser`."""
    for secname, section in sorted(config.items()):
        if secname == "plugins":
            continue

        if not parser.has_section(secname):
            parser.add_section(secname)

        for key in sorted(section):
            value = section[key]
            if isinstance(value, (tuple, list)):
                value = SettingsController.sep.join(value)

            elif isinstance(value, int):
                value = str(value)

            parser.set(secname, key, value)

    # save plugins
    plugins = config["plugins"]
    for secname, section in sorted(plugins.items()):
        if not parser.has_section(secname):
            parser.add_section(secname)

        for key in sorted(section):
            value = section[key]
            if isinstance(value, (tuple, list)):
                value = SettingsController.sep.join(value)

            elif isinstance(value, int):
                value = str(value)

            parser.set(secname, key, value)


class ConfigparserAdapter(pretty.OutputMixin):
    config_filename = "kupfer.cfg"
    defaults_filename = "defaults.cfg"

    def __init__(self):
        self.encoding = _override_encoding(locale.getpreferredencoding())
        self.output_debug("Using", self.encoding)

    def save(self, conf: Configuration) -> None:
        self.output_debug("Saving config")
        config_path = config.save_config_file(self.config_filename + ".new")
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

        # Set up defaults
        confmap = Configuration()
        if config_file := config.get_config_file(self.defaults_filename):
            if parser := self._load_from_file(config_file):
                _fill_configuration_from_parser(parser, confmap)

        confmap.save_as_defaults()

        # load user config file
        if config_file := config.get_config_file(self.config_filename):
            if parser := self._load_from_file(config_file):
                _fill_configuration_from_parser(parser, confmap)

        return confmap


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
        self.output_info("mark_updated", SettingsController._inst)
        if SettingsController._inst is not None:
            self._save_timer.set(60, self._save_config)

    def _save_config(self, _scheduler: ty.Any = None) -> None:
        self._adapter.save(self.config)

    def emit_value_changed(self, section: str, key: str, value: ty.Any) -> None:
        signal = f"value-changed::{section.lower()}.{key.lower()}"
        self.emit(signal, section, key, value)

    def get_plugin_enabled(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is enabled"""
        return self.get_plugin_config_bool(plugin_id, "kupfer_enabled", False)

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> bool:
        """Convenience: set if @plugin_id is enabled"""
        ret = self.set_plugin_config(
            plugin_id, "kupfer_enabled", enabled, value_type=_strbool
        )
        self.emit("plugin-enabled-changed", plugin_id, enabled)
        return ret

    def get_plugin_is_hidden(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is hidden"""
        return self.get_plugin_config_bool(plugin_id, "kupfer_hidden", False)

    @classmethod
    def _source_config_repr(cls, obj: ty.Any) -> str:
        name = type(obj).__name__
        return "".join((c if c.isalnum() else "_") for c in name)

    def get_source_is_toplevel(self, plugin_id: str, src: ty.Any) -> bool:
        key = "kupfer_toplevel_" + self._source_config_repr(src)
        default = not getattr(src, "source_prefer_sublevel", False)
        return self.get_plugin_config_bool(plugin_id, key, default)

    def set_source_is_toplevel(
        self, plugin_id: str, src: ty.Any, value: bool
    ) -> bool:
        key = "kupfer_toplevel_" + self._source_config_repr(src)
        self.emit("plugin-toplevel-changed", plugin_id, value)
        return self.set_plugin_config(
            plugin_id, key, value, value_type=_strbool
        )

    def get_global_keybinding(self, key: str) -> str:
        if key == "keybinding":
            return self.config.kupfer.keybinding

        if key == "magickeybinding":
            return self.config.kupfer.magickeybinding

        raise ValueError("invalid key {key}")

    def set_global_keybinding(self, key: str, val: str) -> bool:
        if key == "keybinding":
            self.config.kupfer.keybinding = val
            return True

        if key == "magickeybinding":
            self.config.kupfer.magickeybinding = val
            return True

        return False

    def get_directories(self, direct: bool = True) -> ty.Iterator[str]:
        """Yield directories to use as directory sources"""
        specialdirs = {
            k: getattr(GLib.UserDirectory, k)
            for k in dir(GLib.UserDirectory)
            if k.startswith("DIRECTORY_")
        }

        def get_special_dir(opt):
            if opt.startswith("USER_"):
                opt = opt[5:]
                if opt in specialdirs:
                    return GLib.get_user_special_dir(specialdirs[opt])

            return None

        cat = (
            self.config.directories.direct
            if direct
            else self.config.directories.catalog
        )
        for direc in cat:
            dpath = get_special_dir(direc)
            yield dpath or os.path.abspath(os.path.expanduser(direc))

    # pylint: disable=too-many-return-statements
    def get_plugin_config(
        self,
        plugin: str,
        key: str,
        value_type: PlugConfigValueType = str,
        default: PlugConfigValue | None = None,
    ) -> PlugConfigValue | None:
        """Return setting @key for plugin names @plugin, try to coerce to
        type @value_type.
        Else return @default if does not exist, or can't be coerced
        """
        plug_section = f"plugin_{plugin}"

        try:
            plug_conf = self.config.plugins[plug_section]
            val = plug_conf[key]
        except KeyError:
            return default

        if val is None:
            return default

        if isinstance(value_type, type) and issubclass(
            value_type, ExtendedSetting
        ):
            val_obj: ExtendedSetting = value_type()
            val_obj.load(plugin, key, val)
            return val_obj

        value = default
        try:
            if value_type is bool:
                value = _strbool(val)
            elif value_type is list:
                assert isinstance(val, str)
                value = _strlist(val)
            elif isinstance(value_type, type):
                value = value_type(val)
            elif isinstance(value_type, ValueConverter):
                value = value_type(val, default=default)  # type: ignore

        except (ValueError, TypeError) as err:
            self.output_info(f"Error for load value {plug_section}.{key}", err)

        return value

    def get_plugin_config_bool(
        self, plugin: str, key: str, default: bool
    ) -> bool:
        res = self.get_plugin_config(plugin, key, _strbool, default)
        assert isinstance(res, bool)
        return res

    def set_plugin_config(
        self,
        plugin: str,
        key: str,
        value: PlugConfigValue,
        value_type: PlugConfigValueType = str,
    ) -> bool:
        """Try set @key for plugin names @plugin, coerce to @value_type first."""

        plug_section = f"plugin_{plugin}"
        self.emit_value_changed(plug_section, key, value)

        value_repr: int | str | float | None

        if isinstance(value, ExtendedSetting):
            value_repr = value.save(plugin, key)
        elif value_type is list:
            value_repr = str(value)
        elif value is None or isinstance(value, (str, float, int)):
            value_repr = value

        if plug_section not in self.config.plugins:
            self.config.plugins[plug_section] = {}

        self.config.plugins[plug_section][key] = value_repr
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
