"""
This is a program of its own, that does not integrate with the
Kupfer process.
"""
import builtins
import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Keybinder", "3.0")

from gi.repository import Gtk, Keybinder as keybinder

import dbus

from dbus.mainloop.glib import DBusGMainLoop

SERV = "se.kaizer.kupfer"
OBJ = "/interface"
IFACE = "se.kaizer.kupfer.Listener"

if not hasattr(builtins, '_'):
    def _(x):
        return x

def get_all_keys():
    try:
        bus = dbus.Bus()
        obj = bus.get_object(SERV, OBJ)
        iface = dbus.Interface(obj, IFACE)
        return iface.GetBoundKeys(byte_arrays=True)
    except dbus.DBusException as exc:
        print(exc)
        print("Waiting for Kupfer to start..")
        return []

def rebind_key(keystring, is_bound):
    if is_bound:
        print("binding", keystring)
        keybinder.bind(keystring, relay_key, keystring)
    else:
        print("unbinding", keystring)
        keybinder.unbind(keystring)

def relay_key(key):
    print("Relaying", key)
    time = keybinder.get_current_event_time()
    s_id = "kupfer-%d_TIME%s" % (os.getpid(), time)
    bus = dbus.Bus()
    obj = bus.get_object(SERV, OBJ, introspect=False)
    iface = dbus.Interface(obj, IFACE)
    iface.RelayKeysFromDisplay(key, os.getenv("DISPLAY", ":0"), s_id)

def main():
    DBusGMainLoop(set_as_default=True)

    relayed_keys = list(get_all_keys())

    for key in relayed_keys:
        rebind_key(key, True)
    bus = dbus.Bus()
    bus.add_signal_receiver(rebind_key, 'BoundKeyChanged',
            dbus_interface=IFACE)
    sicon = Gtk.StatusIcon.new_from_icon_name("kupfer")
    display = os.getenv("DISPLAY", ":0")
    sicon.set_tooltip_text(_("Keyboard relay is active for display %s") % display)
    sicon.set_visible(True)
    try:
        Gtk.main()
    except KeyboardInterrupt:
        raise SystemExit(0)

if __name__ == '__main__':
    main()
