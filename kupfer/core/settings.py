from __future__ import annotations

import configparser
import copy
import locale
import os
import typing as ty
import ast

from gi.repository import GLib, GObject

from kupfer import config
from kupfer.support import pretty, scheduler

AltValidator = ty.Callable[[dict[str, ty.Any]], bool]
Config = dict[str, dict[str, ty.Any]]


@ty.runtime_checkable
class ExtendedSetting(ty.Protocol):
    """Protocol that define non-simple configuration option"""

    def load(self, plugin_id: str, key: str, config_value: str | None) -> None:
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


def strbool(value: ty.Any, default: bool = False) -> bool:
    """Coerce bool from string value or bool"""
    if value in (True, False):
        return value  # type: ignore

    value = str(value).lower()
    if value in ("no", "false"):
        return False

    if value in ("yes", "true"):
        return True

    return default


def strint(value: ty.Any, default: int = 0) -> int:
    """Coerce bool from string value or bool"""
    try:
        return int(value)
    except ValueError:
        return default


def strlist(value: str, default: list[ty.Any] | None = None) -> list[ty.Any]:
    """Parse string into list using ast literal_eval.

    literal_eval handle only 'safe' data, so should work fine.
    """
    try:
        val = ast.literal_eval(value)
        if isinstance(val, list):
            return val

        raise ValueError(f"invalid type: {val!r}")
    except (TypeError, SyntaxError, MemoryError, RecursionError) as err:
        raise ValueError(f"evaluate {value!r} error") from err


def _override_encoding(name: str) -> str | None:
    """Return a new encoding name if we want to override it, else return None.

    This is used to “upgrade” ascii to UTF-8 since the latter is a superset.
    """
    if name.lower() in ("ascii", "ANSI_X3.4-1968".lower()):
        return "UTF-8"

    return None


def _fill_parser_read(
    parser: configparser.RawConfigParser,
    defaults: Config,
) -> None:
    """Add values from `defaults` to `parser`."""
    for secname, section in defaults.items():
        if not parser.has_section(secname):
            parser.add_section(secname)

        for key, default in section.items():
            if isinstance(default, (tuple, list)):
                default = SettingsController.sep.join(default)

            elif isinstance(default, int):
                default = str(default)

            parser.set(secname, key, default)


# pylint: disable=too-many-return-statements
def _parse_value(defval: ty.Any, value: str) -> ty.Any:
    if isinstance(defval, tuple):
        if not value:
            return ()

        return tuple(
            filter(None, map(str.strip, value.split(SettingsController.sep)))
        )

    if isinstance(defval, list):
        if not value:
            return []

        return list(
            filter(None, map(str.strip, value.split(SettingsController.sep)))
        )

    if isinstance(defval, bool):
        return strbool(value)

    if isinstance(defval, int):
        return type(defval)(value)

    return value


def _fill_confmap_fom_parser(
    parser: configparser.RawConfigParser,
    confmap: Config,
    defaults: Config,
) -> None:
    """Put values from `parser` to `confmap` using `defaults` as schema."""
    for secname in parser.sections():
        if secname not in confmap:
            confmap[secname] = {}

        for key in parser.options(secname):
            value = parser.get(secname, key)
            if (sec := defaults.get(secname)) is not None:
                if (defval := sec.get(key)) is not None:
                    value = _parse_value(defval, value)

            confmap[secname][key] = value


def _confmap_difference(conf: Config, defaults: Config) -> Config:
    """Extract the non-default keys to write out"""
    difference = {}
    for secname, section in conf.items():
        if secname not in defaults:
            difference[secname] = section.copy()
            continue

        difference[secname] = {}
        for key, config_val in section.items():
            if (
                secname in defaults
                and key in defaults[secname]
                and defaults[secname][key] == config_val
            ):
                continue

            difference[secname][key] = config_val

        if not difference[secname]:
            difference.pop(secname)

    return difference


def _fill_parser_from_config(
    parser: configparser.RawConfigParser, defaults: Config
) -> None:
    """Put content of `defaults` into `parser`."""
    for secname in sorted(defaults):
        section = defaults[secname]
        if not parser.has_section(secname):
            parser.add_section(secname)

        for key in sorted(section):
            value = section[key]
            if isinstance(value, (tuple, list)):
                value = SettingsController.sep.join(value)

            elif isinstance(value, int):
                value = str(value)

            parser.set(secname, key, value)


# pylint: disable=too-many-public-methods
class SettingsController(GObject.GObject, pretty.OutputMixin):  # type: ignore
    __gtype_name__ = "SettingsController"
    config_filename = "kupfer.cfg"
    defaults_filename = "defaults.cfg"
    sep = ";"
    default_directories = (
        "~/",
        "~/Desktop",
    )
    # Minimal "defaults" to define all fields
    # Read defaults defined in a defaults.cfg file
    _defaults: dict[str, ty.Any] = {
        "Kupfer": {
            "keybinding": "",
            "magickeybinding": "",
            "showstatusicon": True,
            "showstatusicon_ai": False,
            "usecommandkeys": True,
        },
        "Appearance": {
            "icon_large_size": 128,
            "icon_small_size": 24,
            "list_height": 200,
        },
        "Directories": {
            "direct": default_directories,
            "catalog": (),
        },
        "DeepDirectories": {
            "direct": (),
            "catalog": (),
            "depth": 1,
        },
        "Keybindings": {},
        "Tools": {},
    }

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
        self._defaults_path: str | None = None
        self.encoding = _override_encoding(locale.getpreferredencoding())
        self.output_debug("Using", self.encoding)
        self._config = self._read_config()
        self._save_timer = scheduler.Timer(True)
        self._alternatives: dict[str, ty.Any] = {}
        self._alternative_validators: dict[str, AltValidator | None] = {}

    def _update_config_save_timer(self) -> None:
        self._save_timer.set(60, self._save_config)

    def _read_config(self, read_config: bool = True) -> Config:
        """Read cascading config files: default -> then config
        (in all XDG_CONFIG_DIRS)."""
        parser = configparser.RawConfigParser()

        # Set up defaults
        confmap = copy.deepcopy(self._defaults)
        _fill_parser_read(parser, confmap)

        # Read all config files
        config_files: list[str] = []
        try:
            defaults_path = config.get_data_file(self.defaults_filename)
        except config.ResourceLookupError:
            self.output_error(
                f"Error: no default config file {self.defaults_filename} "
                "found!"
            )
        else:
            self._defaults_path = defaults_path
            config_files.append(defaults_path)

        if read_config:
            if config_path := config.get_config_file(self.config_filename):
                config_files.append(config_path)

        for config_file in config_files:
            try:
                parser.read(config_file, encoding=self.encoding)
            except OSError as exc:
                self.output_error(
                    f"Error reading configuration file {config_file}: {exc}"
                )
            except UnicodeDecodeError as exc:
                self.output_error(
                    f"Error reading configuration file {config_file}: {exc}"
                )

        # Read parsed file into the dictionary again
        _fill_confmap_fom_parser(parser, confmap, self._defaults)
        return confmap

    def _save_config(self, _scheduler: ty.Any = None) -> None:
        self.output_debug("Saving config")
        config_path = config.save_config_file(self.config_filename)
        if not config_path:
            self.output_info("Unable to save settings, can't find config dir")
            return

        # read in just the default values
        default_confmap = self._read_config(read_config=False)
        parser = configparser.RawConfigParser()
        confmap = _confmap_difference(self._config, default_confmap)
        _fill_parser_from_config(parser, confmap)
        ## Write to tmp then rename over for it to be atomic
        temp_config_path = f"{config_path}.{os.getpid()}"
        with open(temp_config_path, "w", encoding="UTF_8") as out:
            parser.write(out)

        os.rename(temp_config_path, config_path)

    def get_config(self, section: str, key: str) -> ty.Any:
        """General interface, but section must exist"""
        if section in self._defaults:
            key = key.lower()
            value = self._config[section].get(key)
            return value

        raise KeyError(f"Invalid settings section: {section}")

    def _set_config(self, section: str, key: str, value: ty.Any) -> bool:
        """General interface, but section must exist"""
        self.output_debug("Set", section, key, "to", value)
        key = key.lower()
        oldvalue = self._config[section].get(key)
        if section in self._defaults:
            if oldvalue is None:
                self._config[section][key] = str(value)
            else:
                self._config[section][key] = type(oldvalue)(value)

            self._emit_value_changed(section, key, value)
            self._update_config_save_timer()
            return True

        raise KeyError(f"Invalid settings section: {section}")

    def _emit_value_changed(
        self, section: str, key: str, value: ty.Any
    ) -> None:
        signal = f"value-changed::{section.lower()}.{key.lower()}"
        self.emit(signal, section, key, value)

    def _get_raw_config(self, section: str, key: str) -> str | None:
        """General interface, but section must exist"""
        key = key.lower()
        return self._config[section].get(key)

    def _set_raw_config(
        self, section: str, key: str, value: str | None
    ) -> bool:
        """General interface, but will create section"""
        self.output_debug("Set", section, key, "to", value)
        if section not in self._config:
            self._config[section] = {}

        key = key.lower()
        self._config[section][key] = value
        self._update_config_save_timer()
        return False

    def _get_from_defaults(self, section: str, option: str) -> str | None:
        """Load values from default configuration file."""
        if self._defaults_path is None:
            self.output_error("Defaults not found")
            return None

        parser = configparser.RawConfigParser()
        parser.read(self._defaults_path)
        return parser.get(section, option.lower())

    def _get_from_defaults_section(
        self, section: str
    ) -> list[tuple[str, str]] | None:
        """Load values from default configuration file, return all section
        items as (key, value)."""
        if self._defaults_path is None:
            self.output_error("Defaults not found")
            return None

        parser = configparser.RawConfigParser()
        parser.read(self._defaults_path)
        return parser.items(section)

    def get_config_int(self, section: str, key: str) -> int:
        """section must exist"""
        if section not in self._defaults:
            raise KeyError(f"Invalid settings section: {section}")

        key = key.lower()
        value = self._config[section].get(key)
        return strint(value)

    def get_plugin_enabled(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is enabled"""
        return self.get_plugin_config(  # type: ignore
            plugin_id, "kupfer_enabled", value_type=strbool, default=False
        )

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> bool:
        """Convenience: set if @plugin_id is enabled"""
        ret = self.set_plugin_config(
            plugin_id, "kupfer_enabled", enabled, value_type=strbool
        )
        self.emit("plugin-enabled-changed", plugin_id, enabled)
        return ret

    def get_plugin_is_hidden(self, plugin_id: str) -> bool:
        """Convenience: if @plugin_id is hidden"""
        return self.get_plugin_config(  # type: ignore
            plugin_id, "kupfer_hidden", value_type=strbool, default=False
        )

    @classmethod
    def _source_config_repr(cls, obj: ty.Any) -> str:
        name = type(obj).__name__
        return "".join((c if c.isalnum() else "_") for c in name)

    def get_source_is_toplevel(self, plugin_id: str, src: ty.Any) -> bool:
        key = "kupfer_toplevel_" + self._source_config_repr(src)
        default = not getattr(src, "source_prefer_sublevel", False)
        return self.get_plugin_config(  # type: ignore
            plugin_id, key, value_type=strbool, default=default
        )

    def set_source_is_toplevel(
        self, plugin_id: str, src: ty.Any, value: bool
    ) -> bool:
        key = "kupfer_toplevel_" + self._source_config_repr(src)
        self.emit("plugin-toplevel-changed", plugin_id, value)
        return self.set_plugin_config(plugin_id, key, value, value_type=strbool)

    def get_keybinding(self) -> str:
        """Convenience: Kupfer keybinding as string"""
        return self.get_config("Kupfer", "keybinding")  # type: ignore

    def set_keybinding(self, keystr: str) -> bool:
        """Convenience: Set Kupfer keybinding as string"""
        return self._set_config("Kupfer", "keybinding", keystr)

    def get_magic_keybinding(self) -> str:
        """Convenience: Kupfer alternate keybinding as string"""
        return self.get_config("Kupfer", "magickeybinding")  # type: ignore

    def set_magic_keybinding(self, keystr: str) -> bool:
        """Convenience: Set alternate keybinding as string"""
        return self._set_config("Kupfer", "magickeybinding", keystr)

    def get_global_keybinding(self, key: str) -> str:
        if key == "keybinding":
            return self.get_keybinding()

        if key == "magickeybinding":
            return self.get_magic_keybinding()

        raise ValueError("invalid key {key}")

    def set_global_keybinding(self, key: str, val: str) -> bool:
        if key == "keybinding":
            return self.set_keybinding(val)

        if key == "magickeybinding":
            return self.set_magic_keybinding(val)

        return False

    def get_use_command_keys(self) -> bool:
        return self.get_config("Kupfer", "usecommandkeys")  # type: ignore

    def set_use_command_keys(self, enabled: bool) -> bool:
        return self._set_config("Kupfer", "usecommandkeys", enabled)

    def get_action_accelerator_modifer(self):
        return self.get_config("Kupfer", "action_accelerator_modifer")

    def set_action_accelerator_modifier(self, value: str) -> bool:
        """
        Valid values are: 'alt', 'ctrl'
        """
        return self._set_config("Kupfer", "action_accelerator_modifer", value)

    def set_large_icon_size(self, size: str) -> bool:
        return self._set_config("Appearance", "icon_large_size", size)

    def set_small_icon_size(self, size: str) -> bool:
        return self._set_config("Appearance", "icon_small_size", size)

    def get_show_status_icon(self) -> bool:
        """Convenience: Show icon in notification area as bool (GTK)."""
        return strbool(self.get_config("Kupfer", "showstatusicon"))

    def set_show_status_icon(self, enabled: bool) -> bool:
        """Set config value and return success"""
        return self._set_config("Kupfer", "showstatusicon", enabled)

    def get_show_status_icon_ai(self) -> bool:
        """Convenience: Show icon in notification area as bool (AppIndicator3)"""
        return strbool(self.get_config("Kupfer", "showstatusicon_ai"))

    def set_show_status_icon_ai(self, enabled: bool) -> bool:
        """Set config value and return success"""
        return self._set_config("Kupfer", "showstatusicon_ai", enabled)

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

        level = "Direct" if direct else "Catalog"
        for direc in self.get_config("Directories", level):
            dpath = get_special_dir(direc)
            yield dpath or os.path.abspath(os.path.expanduser(direc))

    def set_directories(self, dirs: list[str]) -> bool:
        return self._set_config("Directories", "direct", dirs)  #

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
        if plug_section not in self._config:
            return default

        val = self._get_raw_config(plug_section, key)
        if val is None:
            return default

        if value_type is ExtendedSetting:
            val_obj: ExtendedSetting = value_type()  # type: ignore
            val_obj.load(plugin, key, val)
            return val_obj

        try:
            if value_type is bool:
                return strbool(val)

            if value_type is list:
                return strlist(val)

            return value_type(val)  # type: ignore
        except ValueError as err:
            self.output_info(
                f"Error for stored value {plug_section}.{key}", err
            )

        return default

    def set_plugin_config(
        self,
        plugin: str,
        key: str,
        value: PlugConfigValue,
        value_type: PlugConfigValueType = str,
    ) -> bool:
        """Try set @key for plugin names @plugin, coerce to @value_type first."""

        plug_section = f"plugin_{plugin}"
        self._emit_value_changed(plug_section, key, value)

        if value_type is ExtendedSetting:
            value_repr = value.save(plugin, key)  # type: ignore

        elif value_type is list:
            value_repr = str(value)

        else:
            value_repr = value

        return self._set_raw_config(plug_section, key, value_repr)

    def get_accelerator(self, name: str | None) -> str | None:
        return self.get_config("Keybindings", name)  # type: ignore

    def set_accelerator(self, name: str, key: str) -> bool:
        return self._set_config("Keybindings", name, key)

    def get_accelerators(self) -> dict[str, ty.Any]:
        return self._config["Keybindings"]

    def reset_keybindings(self) -> None:
        if key := self._get_from_defaults("Kupfer", "keybinding"):
            self.set_keybinding(key)

        if key := self._get_from_defaults("Kupfer", "magickeybinding"):
            self.set_magic_keybinding(key)

    def reset_accelerators(self) -> None:
        for key, value in self._get_from_defaults_section("Keybindings") or ():
            self._set_config("Keybindings", key, value)

    def get_preferred_tool(self, tool_id: str) -> ty.Any:
        """Get preferred ID for a @tool_id.

        Supported: 'terminal', 'editor'
        """
        return self.get_config("Tools", tool_id)

    def set_preferred_tool(self, tool_id: str, value: ty.Any) -> bool:
        return self._set_config("Tools", tool_id, value)

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

    def get_preferred_alternative(self, category_key: str) -> dict[str, ty.Any]:
        """Get preferred alternative dict for @category_key."""
        tool_id = self.get_preferred_tool(category_key)
        alternatives = self._alternatives[category_key]
        if alt := alternatives.get(tool_id):
            return alt  # type: ignore

        self.output_debug("Warning, no configuration for", category_key)
        return next(iter(alternatives.values()), None)  # type: ignore

    def update_alternatives(
        self,
        category_key: str,
        alternatives: dict[str, ty.Any],
        validator: AltValidator | None,
    ) -> None:
        self._alternatives[category_key] = alternatives
        self._alternative_validators[category_key] = validator
        self.emit("alternatives-changed::" + category_key, category_key)


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


def get_configured_terminal() -> dict[str, ty.Any]:
    """Return the configured Terminal object"""
    setctl = get_settings_controller()
    return setctl.get_preferred_alternative("terminal")
