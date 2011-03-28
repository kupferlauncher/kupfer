import os

import gtk
import keybinder
import dbus

SERV = "se.kaizer.kupfer"
OBJ = "/interface"
IFACE = "se.kaizer.kupfer.Listener"


def get_all_keys():
	bus = dbus.Bus()
	obj = bus.get_object(SERV, OBJ)
	iface = dbus.Interface(obj, IFACE)
	return iface.GetBoundKeys(byte_arrays=True)

def relay_key(key):
	print "Relaying", key
	time = keybinder.get_current_event_time()
	s_id = "kupfer-%d_TIME%s" % (os.getpid(), time)
	bus = dbus.Bus()
	obj = bus.get_object(SERV, OBJ)
	iface = dbus.Interface(obj, IFACE)
	iface.RelayKeysFromDisplay(key, os.getenv("DISPLAY"), s_id)

def main():
	relayed_keys = list(get_all_keys())
	for key in relayed_keys:
		keybinder.bind(key, relay_key, key)
	gtk.main()

if __name__ == '__main__':
	main()
