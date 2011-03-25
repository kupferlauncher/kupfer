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

from kupfer.ui import uievents

class AlreadyRunningError (Exception):
	"""Service already available on the bus Exception"""
	pass

class NoConnectionError (Exception):
	"""Not possible to establish connection
	for callbacks"""
	pass

server_name = "se.kaizer.kupfer"
interface_name = "se.kaizer.kupfer.Listener"
object_name = "/interface"

class Service (ExportedGObject):
	def __init__(self):
		"""Create a new Kupfer service on the Session Bus

		Raises NoConnectionError, AlreadyRunningError
		"""
		if not session_bus:
			raise NoConnectionError
		if session_bus.name_has_owner(server_name):
			raise AlreadyRunningError
		bus_name = dbus.service.BusName(server_name, bus=session_bus)
		super(Service, self).__init__(conn=session_bus, object_path=object_name,
				bus_name=bus_name)

	def unregister(self):
		if session_bus:
			session_bus.release_name(server_name)

	@dbus.service.method(interface_name)
	def Present(self):
		self.emit("present")

	@dbus.service.method(interface_name, in_signature="ay",
	                     byte_arrays=True)
	def PresentWithStartup(self, notify_id):
		with uievents.using_startup_notify_id(notify_id):
			self.emit("present")

	@dbus.service.method(interface_name)
	def ShowHide(self):
		self.emit("show-hide")

	@dbus.service.method(interface_name, in_signature="s")
	def PutText(self, text):
		self.emit("put-text", text)

	@dbus.service.method(interface_name, in_signature="as")
	def PutFiles(self, fileuris):
		# files sent with dbus-send from kupfer have a custom comma
		# escape that we have to unescape here
		fileuris[:] = [f.replace("%%kupfercomma%%", ",") for f in fileuris]
		self.emit("put-files", fileuris)

	@dbus.service.method(interface_name, in_signature="s")
	def ExecuteFile(self, filepath):
		self.emit("execute-file", filepath)

	@dbus.service.method(interface_name, in_signature="say",
	                     byte_arrays=True)
	def ExecuteFileWithStartup(self, filepath, notify_id):
		with uievents.using_startup_notify_id(notify_id):
			self.emit("execute-file", filepath)

	@dbus.service.method(interface_name)
	def Quit(self):
		self.emit("quit")

gobject.signal_new("present", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

gobject.signal_new("show-hide", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

gobject.signal_new("put-text", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, ))

gobject.signal_new("put-files", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))

gobject.signal_new("execute-file", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING,))

gobject.signal_new("quit", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

