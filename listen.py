#!/usr/bin/env python

"""
This module is a singelton, that sets up callbacks to dbus signals
"""

import dbus
import dbus.glib

session_bus = dbus.Bus()
interface_name = "org.gnome.Kupfer"

def register(signal_name, callback):
	"""
	Register function `callback` for `signal_name`
	"""
	session_bus.add_signal_receiver(callback, signal_name, interface_name, bus_name=None, path=None)


if __name__ == '__main__':
	def signal_callback(signal=None):
		    print "Received signal %s" % signal

	import gtk
	register("activate", signal_callback)
	# Enter the event loop, waiting for signals
	gtk.main()
