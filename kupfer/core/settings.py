from __future__ import annotations

import configparser
import locale
import os
import typing as ty
import ast
from dataclasses import dataclass, field, is_dataclass, asdict

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


@dataclass
class ConfBase:
    def __setattr__(self, name, value):
        if field := self.__dataclass_fields__.get(name):
            field_type = field.type
            if (
                isinstance(value, str)
                and field_type is not str
                and value is not None
            ):
                if field_type is int or field_type == "int":
                    value = _strint(value)
                elif field_type is bool or field_type == "bool":
                    value = _strbool(value)
                elif field.default_factory is list or str(
                    field_type
                ).startswith("list["):
                    value = _strlist(value)
            try:
                old_val = getattr(self, name)
                # notify about value changed
                if old_val != value:
                    if SettingsController._inst:
                        SettingsController._inst.mark_updated()
            except AttributeError:
                pass
        else:
            pretty.print_error("unknown parameter", name, value)

        super().__setattr__(name, value)

    def get_default_value(self, field_name: str) -> ty.Any:
        """Get default value for `field_name`."""
        field = self.__dataclass_fields__.get(field_name)
        if not field:
            return None

        # either default or default_factory is set so this is safe
        default = field.default
        try:
            default = field.default_factory()  # type: ignore
        except TypeError:
            pass

        return default

    def asdict_non_default(self) -> dict[str, ty.Any]:
        """Get dict of attributes that differ from default. For
        dict only first level is compared."""
        res = {}

        for key, val in self.__dict__.items():
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


@dataclass
class ConfKupfer(ConfBase):
    # Kupfer keybinding as string
    keybinding: str = "<Ctrl>space"
    # Kupfer alternate keybinding as string
    magickeybinding: str = ""
    showstatusicon: bool = True
    showstatusicon_ai: bool = False
    usecommandkeys: bool = True
    action_accelerator_modifer: str = "ctrl"


@dataclass
class ConfAppearance(ConfBase):
    icon_large_size: int = 128
    icon_small_size: int = 24
    list_height: int = 250
    ellipsize_mode: int = 0


@dataclass
class ConfDirectories(ConfBase):
    direct: list[str] = field(
        default_factory=lambda: ["~/", "~/Desktop", "USER_DIRECTORY_DESKTOP"]
    )
    catalog: list[str] = field(default_factory=list)


@dataclass
class ConfDeepDirectories(ConfBase):
    direct: list[str] = field(default_factory=list)
    catalog: list[str] = field(default_factory=list)
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

    set_enabled("plugin_core", True)
    set_enabled("plugin_applications", True)
    set_enabled("plugin_archivemanager", True)
    set_enabled("plugin_calculator", True)
    set_enabled("plugin_clipboard", True)
    set_enabled("plugin_commands", True)
    set_enabled("plugin_dictionary", True)
    set_enabled("plugin_documents", True)
    set_enabled("plugin_favorites", True)
    set_enabled("plugin_fileactions", False)
    set_enabled("plugin_qsicons", True)
    set_enabled("plugin_session_gnome", False)
    set_enabled("plugin_session_xfce", False)
    set_enabled("plugin_screen", False)
    set_enabled("plugin_show_text", True)
    set_enabled("plugin_tracker1", False)
    set_enabled("plugin_triggers", True)
    set_enabled("plugin_trash", True)
    set_enabled("plugin_urlactions", True)
    set_enabled("plugin_volumes", True)
    set_enabled("plugin_wikipedia", True)
    set_enabled("plugin_windows", False)

    res["plugin_core"]["kupfer_hidden"] = True

    return res


@dataclass
class Configuration(ConfBase):
    kupfer: ConfKupfer = field(default_factory=ConfKupfer)
    appearance: ConfAppearance = field(default_factory=ConfAppearance)
    directories: ConfDirectories = field(default_factory=ConfDirectories)
    deepdirectories: ConfDeepDirectories = field(
        default_factory=ConfDeepDirectories
    )

    keybindings: dict[str, ty.Any] = field(default_factory=_default_keybindings)
    tools: dict[str, ty.Any] = field(default_factory=_default_tools)
    plugins: dict[str, dict[str, ty.Any]] = field(
        default_factory=_default_plugins
    )

    def asdict(self) -> dict[str, ty.Any]:
        res = asdict(self)
        try:
            if plugins := res.pop("plugins"):
                for key, val in plugins.items():
                    res[key] = val
        except KeyError:
            pass

        return res


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


def _fill_configuration_fom_parser(
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
        elif is_dataclass(sobj):
            for key, val in parser[secname].items():
                setattr(sobj, key.lower(), val)
        else:
            pretty.print_error("unknown secname", secname, sobj)


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

    def load(self, read_config: bool = True) -> Configuration:
        """Read cascading config files: default -> then config
        (in all XDG_CONFIG_DIRS)."""
        parser = configparser.RawConfigParser()

        # Set up defaults
        confmap = Configuration()

        # load user config file
        if config_file := config.get_config_file(self.config_filename):
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
        _fill_configuration_fom_parser(parser, confmap)
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

    # def get_config(self, section: str, key: str) -> ty.Any:
    #     """General interface, but section must exist"""
    #     # TODO: drop
    #     obj = getattr(self.config, section.lower())
    #     val = getattr(obj, key.lower())
    #     return val

    # def set_config(self, section: str, key: str, value: ty.Any) -> bool:
    #     """General interface, but section must exist"""
    #     key = key.lower()
    #     dobj = getattr(self.config, section.lower())
    #     if is_dataclass(dobj):
    #         setattr(dobj, key, value)
    #         return True

    #     return False

    def mark_updated(self):
        self.output_info("mark_updated", SettingsController._inst)
        if SettingsController._inst is not None:
            self._save_timer.set(60, self._save_config)

    def _save_config(self, _scheduler: ty.Any = None) -> None:
        self._adapter.save(self.config)

    def emit_value_changed(self, section: str, key: str, value: ty.Any) -> None:
        signal = f"value-changed::{section.lower()}.{key.lower()}"
        self.emit(signal, section, key, value)

    # def get_config_int(self, section: str, key: str) -> int:
    #     """section must exist"""
    #     # TODO
    #     obj = getattr(self.config, section.lower())
    #     val = getattr(obj, key)
    #     return _strint(val)

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

    def get_action_accelerator_modifer(self) -> str:
        return self.config.kupfer.action_accelerator_modifer
        # return str(self.get_config("Kupfer", "action_accelerator_modifer"))

    def set_action_accelerator_modifier(self, value: str) -> bool:
        """
        Valid values are: 'alt', 'ctrl'
        """
        self.config.kupfer.action_accelerator_modifer = value
        return True
        # return self.set_config("Kupfer", "action_accelerator_modifer", value)

    def set_large_icon_size(self, size: str) -> bool:
        self.config.appearance.icon_large_size = _strint(size)
        return True
        # return self.set_config("Appearance", "icon_large_size", size)

    def set_small_icon_size(self, size: str) -> bool:
        self.config.appearance.icon_small_size = _strint(size)
        return True
        # return self.set_config("Appearance", "icon_small_size", size)

    def get_show_status_icon(self) -> bool:
        """Convenience: Show icon in notification area as bool (GTK)."""
        return self.config.kupfer.showstatusicon
        # return _strbool(self.get_config("Kupfer", "showstatusicon"))

    def set_show_status_icon(self, enabled: bool) -> bool:
        """Set config value and return success"""
        self.config.kupfer.showstatusicon = enabled
        return True
        # return self.set_config("Kupfer", "showstatusicon", enabled)

    def get_show_status_icon_ai(self) -> bool:
        """Convenience: Show icon in notification area as bool (AppIndicator3)"""
        return self.config.kupfer.showstatusicon_ai
        # return _strbool(self.get_config("Kupfer", "showstatusicon_ai"))

    def set_show_status_icon_ai(self, enabled: bool) -> bool:
        """Set config value and return success"""
        self.config.kupfer.showstatusicon_ai = enabled
        return True
        # return self.set_config("Kupfer", "showstatusicon_ai", enabled)

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

    def set_directories(self, dirs: list[str]) -> bool:
        self.config.directories.direct = dirs
        return True
        # return self.set_config("Directories", "direct", dirs)  #

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
        self.config.kupfer.keybinding = self.config.kupfer.get_default_value(
            "keybinding"
        )
        self.config.kupfer.magickeybinding = (
            self.config.kupfer.get_default_value("magickeybinding")
        )

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
