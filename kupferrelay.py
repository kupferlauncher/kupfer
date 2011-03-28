import os

import gtk
import keybinder
import dbus
import pickle

import kupfer.puid
import kupfer.config
import kupfer.core.settings


SERV = "se.kaizer.kupfer"
OBJ = "/interface"
IFACE = "se.kaizer.kupfer.Listener"


def get_core_keys():
	""" Get configured keys """
	sc = kupfer.core.settings.SettingsController()
	return [sc.get_keybinding(), sc.get_magic_keybinding()]

def get_trigger_keys():
	""" Get configured keys """
	c = kupfer.config.get_config_file("config-kupfer.plugin.triggers-v1.pickle")
	if not c:
		print "No triggers configured"
		return
	with open(c, "rb") as f:
		data_dic = pickle.load(f)
	if not data_dic:
		print "Triggers not configured"
		return
	for target in data_dic['triggers']:
		keystr, name, puid = data_dic['triggers'][target]
		yield keystr

def relay_key(key):
	print "Relaying", key
	time = keybinder.get_current_event_time()
	s_id = "kupfer-%d_TIME%s" % (os.getpid(), time)
	bus = dbus.Bus()
	obj = bus.get_object(SERV, OBJ)
	iface = dbus.Interface(obj, IFACE)
	iface.RelayKeysFromDisplay(key, os.getenv("DISPLAY"), s_id)

def main():
	relayed_keys = []
	relayed_keys.extend(get_core_keys())
	relayed_keys.extend(get_trigger_keys())
	for key in relayed_keys:
		keybinder.bind(key, relay_key, key)

	gtk.main()

if __name__ == '__main__':
	main()
