"""
This module is a singelton, that sets up callbacks to dbus signals
"""

try:
	import dbus
	import dbus.glib

# if dbus unavailable print the exception here
# but further actions (register) will fail without warning
	session_bus = dbus.Bus()
except (ImportError, dbus.exceptions.DBusException), exc:
	session_bus = None
	print exc

interface_name = "org.gnome.Kupfer"

def register(signal_name, callback):
	"""
	Register function `callback` for `signal_name`
	"""
	if session_bus:
		session_bus.add_signal_receiver(callback, signal_name, interface_name, bus_name=None, path=None)

