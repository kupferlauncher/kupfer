"""
This module is a singelton, that sets up callbacks to dbus signals
"""

import gobject
try:
	import dbus
	import dbus.glib
	from dbus.gobject_service import ExportedGObject

# if dbus unavailable print the exception here
# but further actions (register) will fail without warning
	session_bus = dbus.Bus()
except (ImportError, dbus.exceptions.DBusException), exc:
	session_bus = None
	print exc

server_name = "se.kaizer.kupfer"
interface_name = "se.kaizer.kupfer.Listener"
object_name = "/interface"

class _Service (ExportedGObject):
	@dbus.service.method(interface_name)
	def Present(self):
		self.emit("present")
	@dbus.service.method(interface_name)
	def ShowHide(self):
		self.emit("show-hide")
	@dbus.service.method(interface_name)
	def Quit(self):
		self.emit("quit")
gobject.signal_new("present", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("show-hide", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("quit", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

_Service_obj = None

def Service():
	"""
	Return a service object, None if dbus not available
	"""
	if not session_bus:
		return None
	global _Service_obj
	if not _Service_obj:
		bus_name = dbus.service.BusName(server_name, bus=session_bus)
		_Service_obj = _Service(bus_name, object_path=object_name)
	return _Service_obj

