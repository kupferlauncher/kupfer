from __future__ import annotations

import typing as ty
import shutil
from gettext import gettext as _, ngettext

from gi.repository import GObject

from kupfer.core import plugins, settings
from kupfer.support import fileutils, pretty

__all__ = [
    "UserNamePassword",
    "PluginSettings",
    "check_dbus_connection",
    "check_keyring_support",
]


def _is_core_setting(key: str) -> bool:
    return key.startswith("kupfer_")


SettingChangeCB = ty.Callable[[ty.Any, str, ty.Any], None]


class PluginSettings(GObject.GObject, pretty.OutputMixin):  # type:ignore
    """Allows plugins to have preferences by assigning an instance
    of this class to the plugin's __kupfer_settings__ attribute.

    Setting values are accessed by the getitem operator [] with
    the setting's 'key' attribute

    Signals:

        plugin-setting-changed: key, value

    """

    __gtype_name__ = "PluginSettings"

    def __init__(self, *setdescs: dict[str, ty.Any]) -> None:
        """Create a settings collection by passing in dictionaries
        as arguments, where each dictionary must have the following keys:
            key
            type
            value (default value)
            label (localized label)

        the @key may be any string except strings starting with
        'kupfer_', which are reserved
        """
        GObject.GObject.__init__(self)
        self.setting_descriptions: dict[str, dict[str, ty.Any]] = {}
        self.setting_key_order: list[str] = []
        self.signal_connection: int = -1
        req_keys = {"key", "value", "type", "label"}
        for desc in setdescs:
            if not req_keys.issubset(list(desc.keys())):
                missing = req_keys.difference(list(desc.keys()))
                raise KeyError(f"Plugin setting missing keys: {missing}")

            if _is_core_setting(desc["key"]):
                raise KeyError(f"Reserved plugin setting key: {desc['key']!r}")

            self.setting_descriptions[desc["key"]] = desc.copy()
            self.setting_key_order.append(desc["key"])

    def __iter__(self) -> ty.Iterator[str]:
        return iter(self.setting_key_order)

    def initialize(self, plugin_name: str) -> None:
        """Init by reading from global settings and setting up callbacks"""
        setctl = settings.get_settings_controller()
        for key in self:
            value_type = self.setting_descriptions[key]["type"]
            value = setctl.get_plugin_config(plugin_name, key, value_type)
            if value is not None:
                self[key] = value

            elif _is_core_setting(key):
                default = self.setting_descriptions[key]["value"]
                setctl.set_plugin_config(plugin_name, key, default, value_type)

        setctl.connect("value-changed", self._on_value_changed, plugin_name)
        # register for unload notification
        if not plugin_name.startswith("core."):
            plugins.register_plugin_unimport_hook(
                plugin_name, self._disconnect_all, plugin_name
            )

    def __getitem__(self, key: str) -> ty.Any:
        return self.setting_descriptions[key]["value"]

    def __setitem__(self, key: str, value: ty.Any) -> None:
        value_type = self.setting_descriptions[key]["type"]
        self.setting_descriptions[key]["value"] = value_type(value)
        if not _is_core_setting(key):
            self.emit(f"plugin-setting-changed::{key}", key, value)

    def _on_value_changed(
        self,
        setctl: settings.SettingsController,
        section: str,
        key: str,
        value: ty.Any,
        plugin_name: str,
    ) -> None:
        """Preferences changed, update object"""
        if key in self and plugin_name in section:
            self[key] = value

    def get_value_type(self, key: str) -> ty.Type[ty.Any]:
        """Return type of setting @key"""
        return ty.cast(ty.Type[ty.Any], self.setting_descriptions[key]["type"])

    def get_label(self, key: str) -> str:
        """Return label for setting @key"""
        return ty.cast(str, self.setting_descriptions[key]["label"])

    def get_alternatives(self, key: str) -> ty.Iterable[ty.Any] | None:
        """Return alternatives for setting @key (if any)"""
        return self.setting_descriptions[key].get("alternatives")

    def get_tooltip(self, key: str) -> str | None:
        """Return tooltip string for setting @key (if any)"""
        return self.setting_descriptions[key].get("tooltip")

    def get_parameter(
        self, key: str, name: str, default: ty.Any = None
    ) -> ty.Any:
        return self.setting_descriptions[key].get(name, default)

    def connect_settings_changed_cb(
        self, callback: SettingChangeCB, *args: ty.Any
    ) -> None:
        self.signal_connection = self.connect(
            "plugin-setting-changed", callback, *args
        )

    def _disconnect_all(self, plugin_name: str) -> None:
        if self.signal_connection != -1:
            self.disconnect(self.signal_connection)


# Arguments: Key, Value
# Detailed by the key
GObject.signal_new(
    "plugin-setting-changed",
    PluginSettings,
    GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.DETAILED,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_PYOBJECT),
)

# Plugin convenience functions for dependencies


# pylint: disable=too-few-public-methods
class _DBusChecker:
    has_connection: bool | None = None

    @classmethod
    def check(cls) -> bool:
        if cls.has_connection is None:
            try:
                import dbus  # pylint: disable=import-outside-toplevel

                dbus.Bus()
                cls.has_connection = True
            except (ImportError, dbus.DBusException):
                cls.has_connection = False

        assert cls.has_connection is not None
        return cls.has_connection


def check_dbus_connection() -> None:
    """Check if a connection to the D-Bus daemon is available,
    else raise ImportError with an explanatory error message.

    For plugins that can not be used without contact with D-Bus;
    if this check is used, the plugin may use D-Bus and assume it
    is available in the Plugin's code.
    """
    if not _DBusChecker.check():
        raise ImportError(_("No D-Bus connection to desktop session"))


# pylint: disable=too-few-public-methods
class UserNamePassword:
    pass


def check_keyring_support() -> None:
    """raise ImportError with because it is not supported."""
    raise ImportError("Keyring is not supported")


def check_keybinding_support() -> None:
    """Check if we can make global keybindings."""
    from kupfer.ui import keybindings  # pylint: disable=import-outside-toplevel

    if not keybindings.is_available():
        raise ImportError(_("Dependency '%s' is not available") % "Keybinder")


def _plugin_configuration_error(plugin: str, err: ty.Any) -> None:
    pretty.print_error(__name__, err)


def _is_valid_terminal(term_dict: dict[str, ty.Any]) -> bool:
    if len(term_dict["argv"]) < 1:
        return False

    exe = term_dict["argv"][0]
    return bool(fileutils.lookup_exec_path(exe))


_AVAILABLE_ALTERNATIVES: ty.Final[dict[str, dict[str, ty.Any]]] = {
    "terminal": {
        "filter": _is_valid_terminal,
        "required_keys": {
            "name": str,
            "argv": list,
            "exearg": str,
            "desktopid": str,
            "startup_notify": bool,
        },
    },
    "editor": {
        "filter": None,
        "required_keys": {
            "name": str,
            "argv": list,
            "terminal": bool,
        },
    },
    "icon_renderer": {
        "filter": None,
        "required_keys": {
            "name": str,
            "renderer": object,
        },
    },
}

_ALTERNATIVES: dict[str, dict[str, ty.Any]] = {
    "terminal": {},
    "editor": {},
    "icon_renderer": {},
}


def register_alternative(
    caller: str, category_key: str, id_: str, **kwargs: ty.Any
) -> bool:
    """Register a new alternative for the category @category_key.

    @caller: Must be the caller's plugin id (Plugin __name__ variable)

    @id_ is a string identifier for the object to register
    @kwargs are the keyed arguments for the alternative constructor

    Returns True with success
    """
    if category_key not in _AVAILABLE_ALTERNATIVES:
        _plugin_configuration_error(
            caller, f"Category '{category_key}' does not exist"
        )
        return False

    full_id = f"{caller}.{id_}"
    kw_set = set(kwargs)
    alt = _AVAILABLE_ALTERNATIVES[category_key]
    req_set = set(alt["required_keys"])

    if full_id in _ALTERNATIVES[category_key]:
        pretty.print_debug(
            __name__, f"Alternative {full_id} already defined in {category_key}"
        )
        return False

    if not req_set.issubset(kw_set):
        _plugin_configuration_error(
            caller, f"Configuration error for alternative '{category_key}':"
        )
        _plugin_configuration_error(caller, f"Missing keys: {req_set - kw_set}")
        return False

    _ALTERNATIVES[category_key][full_id] = kwargs
    pretty.print_debug(
        __name__, f"Registered alternative {category_key}: {full_id}"
    )
    setctl = settings.get_settings_controller()
    setctl.update_alternatives(
        category_key, _ALTERNATIVES[category_key], alt["filter"]
    )

    # register the alternative to be unloaded
    plugin_id = ".".join(caller.split(".")[2:])
    if plugin_id and not plugin_id.startswith("core."):
        plugins.register_plugin_unimport_hook(
            plugin_id, _unregister_alternative, caller, category_key, full_id
        )

    return True


def _unregister_alternative(
    caller: str, category_key: str, full_id: str
) -> None:
    """Remove the alternative for category @category_key
    (this is done automatically at plugin unload)
    """
    if category_key not in _AVAILABLE_ALTERNATIVES:
        _plugin_configuration_error(
            caller, f"Category '{category_key}' does not exist"
        )
        return

    alt = _AVAILABLE_ALTERNATIVES[category_key]
    try:
        del _ALTERNATIVES[category_key][full_id]
    except KeyError:
        _plugin_configuration_error(
            caller, f"Alternative '{full_id}' does not exist"
        )
        return

    pretty.print_debug(
        __name__, f"Unregistered alternative {category_key}: {full_id}"
    )
    setctl = settings.get_settings_controller()
    setctl.update_alternatives(
        category_key, _ALTERNATIVES[category_key], alt["filter"]
    )


def check_command_available(*cmd: str) -> None:
    """Check if the commands is available in system, throw ImportError when not"""
    missing = [f'"{c}"' for c in cmd if not shutil.which(c)]
    if not missing:
        return

    raise ImportError(
        ngettext(
            "Command %(msg)s is not available.",
            "Commands %(msg)s are not available.",
            len(missing),
        )
        % {"msg": ", ".join(missing)}
    )


def check_any_command_available(*cmd: str) -> None:
    """Check if any of command is available in system, throw ImportError when not"""
    for c in cmd:
        if shutil.which(c):
            return

    raise ImportError(
        _("None of commands %(msg)s is available.")
        % {"msg": ", ".join(f'"{c}"' for c in cmd)}
    )
