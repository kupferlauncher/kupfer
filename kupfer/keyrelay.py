"""
This is a program of its own, that does not integrate with the
Kupfer process.
"""
import builtins
import os

import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

gi.require_version("Gtk", "3.0")
gi.require_version("Keybinder", "3.0")

# pylint: disable=wrong-import-position
from gi.repository import Gtk, Keybinder  # noqa:E402

SERV = "se.kaizer.kupfer"
OBJ = "/interface"
IFACE = "se.kaizer.kupfer.Listener"

if not hasattr(builtins, "_"):
    _ = str


def _get_all_keys() -> list[str]:
    try:
        bus = dbus.Bus()
        obj = bus.get_object(SERV, OBJ)
        iface = dbus.Interface(obj, IFACE)
        return iface.GetBoundKeys(byte_arrays=True)  # type: ignore
    except dbus.DBusException as exc:
        print(exc)
        print("Waiting for Kupfer to start..")
        return []


def _rebind_key(keystring: str, is_bound: bool) -> None:
    if is_bound:
        print("binding", keystring)
        Keybinder.bind(keystring, _relay_key, keystring)
    else:
        print("unbinding", keystring)
        Keybinder.unbind(keystring)


def _relay_key(key: str) -> None:
    print("Relaying", key)
    time = Keybinder.get_current_event_time()
    s_id = f"kupfer-{os.getpid()}_TIME{time}"
    bus = dbus.Bus()
    obj = bus.get_object(SERV, OBJ, introspect=False)
    iface = dbus.Interface(obj, IFACE)
    iface.RelayKeysFromDisplay(key, os.getenv("DISPLAY", ":0"), s_id)


def main() -> None:
    DBusGMainLoop(set_as_default=True)

    for key in _get_all_keys():
        _rebind_key(key, True)

    bus = dbus.Bus()
    bus.add_signal_receiver(
        _rebind_key, "BoundKeyChanged", dbus_interface=IFACE
    )
    sicon = Gtk.StatusIcon.new_from_icon_name("kupfer")
    display = os.getenv("DISPLAY", ":0")
    sicon.set_tooltip_text(
        _("Keyboard relay is active for display %s") % display
    )
    sicon.set_visible(True)
    try:
        Gtk.main()
    except KeyboardInterrupt as exc:
        raise SystemExit(0) from exc


if __name__ == "__main__":
    main()
