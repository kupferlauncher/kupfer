"""
This module has a singleton Service for dbus callbacks,
and ensures there is only one unique service in the Session
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

class AlreadyRunning (Exception):
	"""Service already available on the bus Exception"""
	pass

class NoConnection (Exception):
	"""Not possible to establish connection
	for callbacks"""
	pass

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
	@dbus.service.method(interface_name, in_signature="ss")
	def PutText(self, working_directory, text):
		self.emit("put-text", working_directory, text)
	@dbus.service.method(interface_name)
	def Quit(self):
		self.emit("quit")
gobject.signal_new("present", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("show-hide", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("put-text", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_STRING))
gobject.signal_new("quit", _Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

_Service_obj = None

def Service():
	"""
	Return a service object, None if dbus not available

	If a service is already running on the bus,
	raise AlreadyRunning
	"""
	global _Service_obj

	if session_bus and not _Service_obj:
		if session_bus.name_has_owner(server_name):
			raise AlreadyRunning
		bus_name = dbus.service.BusName(server_name, bus=session_bus)
		_Service_obj = _Service(bus_name, object_path=object_name)
	if not _Service_obj:
		raise NoConnection

	return _Service_obj

def Unregister():
	if session_bus:
		session_bus.release_name(server_name)
