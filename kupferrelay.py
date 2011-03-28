import os

import gtk
import keybinder
import dbus

from dbus.mainloop.glib import DBusGMainLoop

SERV = "se.kaizer.kupfer"
OBJ = "/interface"
IFACE = "se.kaizer.kupfer.Listener"


def get_all_keys():
	bus = dbus.Bus()
	obj = bus.get_object(SERV, OBJ)
	iface = dbus.Interface(obj, IFACE)
	return iface.GetBoundKeys(byte_arrays=True)

def rebind_key(keystring, is_bound):
	if is_bound:
		print "binding", keystring
		keybinder.bind(keystring, relay_key, keystring)
	else:
		print "unbinding", keystring
		keybinder.unbind(keystring)

def relay_key(key):
	print "Relaying", key
	time = keybinder.get_current_event_time()
	s_id = "kupfer-%d_TIME%s" % (os.getpid(), time)
	bus = dbus.Bus()
	obj = bus.get_object(SERV, OBJ)
	iface = dbus.Interface(obj, IFACE)
	iface.RelayKeysFromDisplay(key, os.getenv("DISPLAY"), s_id)

def main():
	DBusGMainLoop(set_as_default=True)

	bus = dbus.Bus()
	relayed_keys = list(get_all_keys())

	for key in relayed_keys:
		keybinder.bind(key, relay_key, key)
	bus.add_signal_receiver(rebind_key, 'BoundKeyChanged',
			dbus_interface=IFACE)
	gtk.main()

if __name__ == '__main__':
	main()
