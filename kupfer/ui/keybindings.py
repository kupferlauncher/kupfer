from __future__ import annotations

import typing as ty

import gi
from gi.repository import Gdk, GObject

from kupfer import environment
from kupfer.support import pretty

Keybinder = None  # pylint: disable=invalid-name
if environment.allows_keybinder():
    try:
        gi.require_version("Keybinder", "3.0")

        # pylint: disable=ungrouped-imports
        from gi.repository import Keybinder  # type:ignore

        Keybinder.init()  # type:ignore
    except (ValueError, ImportError):
        pretty.print_debug(__name__, "Keybinder 3.0 not available in gi")
        Keybinder = None

else:
    pretty.print_debug(__name__, "Keybinder disabled")

KeybindingTarget = int

KEYBINDING_TARGET_DEFAULT = 1
KEYBINDING_TARGET_MAGIC = 2
KEYRANGE_RESERVED = (3, 0x1000)
# range for custom keybingings
KEYRANGE_TRIGGERS = (0x1000, 0x2000)


def get_keybound_object():
    """Get the shared instance"""
    return KeyboundObject.instance()


class KeyboundObject(GObject.GObject):  # type:ignore
    """Keybinder object

    signals:
        keybinding (target, event_time)
        keybinding signal is triggered when the key bound
        for @target is triggered.
    """

    __gtype_name__ = "KeyboundObject"
    _instance: KeyboundObject | None = None

    @classmethod
    def instance(cls) -> KeyboundObject:
        if cls._instance is None:
            cls._instance = KeyboundObject()

        return cls._instance

    def keybinding(self, target: int) -> None:
        assert Keybinder
        time = Keybinder.get_current_event_time()
        self.emit("keybinding", target, "", time)

    def emit_bound_key_changed(self, keystring: str, is_bound: bool) -> None:
        self.emit("bound-key-changed", keystring, is_bound)

    def relayed_keys(
        self,
        _sender: ty.Any,
        keystring: str,
        display: Gdk.Display,
        timestamp: float,
    ) -> None:
        for target, key in _CURRENTLY_BOUND.items():
            if keystring == key:
                self.emit("keybinding", target, display, timestamp)


# Arguments: Target, Display, Timestamp
GObject.signal_new(
    "keybinding",
    KeyboundObject,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_INT, GObject.TYPE_STRING, GObject.TYPE_UINT),
)
# Arguments: Keystring, Boolean
GObject.signal_new(
    "bound-key-changed",
    KeyboundObject,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (
        GObject.TYPE_STRING,
        GObject.TYPE_BOOLEAN,
    ),
)

_CURRENTLY_BOUND: dict[int, str | None] = {}


def is_available():
    """
    Return True if keybindings are available.
    """
    if Keybinder is None:
        return False

    try:
        return Keybinder.supported()
    except AttributeError:
        return True


def get_all_bound_keys() -> list[str]:
    return list(filter(None, _CURRENTLY_BOUND.values()))


def get_current_event_time() -> int | float:
    "Return current event time as given by keybinder"
    if Keybinder is None:
        return 0

    return Keybinder.get_current_event_time()


def _register_bound_key(keystr: str | None, target: int) -> None:
    _CURRENTLY_BOUND[target] = keystr


def _get_currently_bound_key(
    target: KeybindingTarget = KEYBINDING_TARGET_DEFAULT,
) -> str | None:
    return _CURRENTLY_BOUND.get(target)


def bind_key(
    keystr: str | None,
    keybinding_target: KeybindingTarget = KEYBINDING_TARGET_DEFAULT,
) -> bool:
    """
    Bind @keystr, unbinding any previous key for @keybinding_target.
    If @keystr is a false value, any previous key will be unbound.
    """
    if Keybinder is None:
        return False

    if not _is_sane_keybinding(keystr):
        pretty.print_error(__name__, "Refusing to bind key", repr(keystr))
        return False

    succ = True
    if keystr:

        def callback(keystr: str) -> bool:
            get_keybound_object().keybinding(keybinding_target)
            return False

        try:
            succ = Keybinder.bind(keystr, callback)
            pretty.print_debug(__name__, "binding", repr(keystr))
            get_keybound_object().emit_bound_key_changed(keystr, True)
        except KeyError as exc:
            pretty.print_error(__name__, exc)
            succ = False

    if succ:
        old_keystr = _get_currently_bound_key(keybinding_target)
        if old_keystr and old_keystr != keystr:
            Keybinder.unbind(old_keystr)
            pretty.print_debug(__name__, "unbinding", repr(old_keystr))
            get_keybound_object().emit_bound_key_changed(old_keystr, False)

        _register_bound_key(keystr, keybinding_target)

    return succ


def _is_sane_keybinding(keystr: str | None) -> bool:
    "Refuse keys that we absolutely do not want to bind"
    if keystr is None:
        return True

    if len(keystr) == 1 and keystr.isalnum():
        return False

    if keystr in ("Return", "space", "BackSpace", "Escape"):
        return False

    return True
