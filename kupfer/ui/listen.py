"""
This module has a singleton Service for dbus callbacks,
and ensures there is only one unique service in the Session
"""

import gobject

try:
	import dbus
	import dbus.glib
	import dbus.service
	from kupfer.dbuscompat import ExportedGObject

	dbus.glib.threads_init()

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
		self.PresentOnDisplay("", "")

	@dbus.service.method(interface_name, in_signature="ay",
	                     byte_arrays=True)
	def PresentWithStartup(self, notify_id):
		self.PresentOnDisplay("", notify_id)

	@dbus.service.method(interface_name, in_signature="ayay",
	                     byte_arrays=True)
	def PresentOnDisplay(self, display, notify_id):
		with uievents.using_startup_notify_id(notify_id) as time:
			self.emit("present", display, time)

	@dbus.service.method(interface_name)
	def ShowHide(self):
		self.emit("show-hide", "", 0)

	@dbus.service.method(interface_name, in_signature="s")
	def PutText(self, text):
		self.PutTextOnDisplay(text, "", "")

	@dbus.service.method(interface_name, in_signature="sayay",
	                     byte_arrays=True)
	def PutTextOnDisplay(self, text, display, notify_id):
		with uievents.using_startup_notify_id(notify_id) as time:
			self.emit("put-text", text, display, time)

	@dbus.service.method(interface_name, in_signature="as")
	def PutFiles(self, fileuris):
		self.PutFilesOnDisplay(fileuris, "", "")

	@dbus.service.method(interface_name, in_signature="asayay",
	                     byte_arrays=True)
	def PutFilesOnDisplay(self, fileuris, display, notify_id):
		# files sent with dbus-send from kupfer have a custom comma
		# escape that we have to unescape here
		fileuris[:] = [f.replace("%%kupfercomma%%", ",") for f in fileuris]
		with uievents.using_startup_notify_id(notify_id) as time:
			self.emit("put-files", fileuris, display, time)

	@dbus.service.method(interface_name, in_signature="s")
	def ExecuteFile(self, filepath):
		self.ExecuteFileOnDisplay(filepath, "", "")

	@dbus.service.method(interface_name, in_signature="sayay",
	                     byte_arrays=True)
	def ExecuteFileOnDisplay(self, filepath, display, notify_id):
		with uievents.using_startup_notify_id(notify_id) as time:
			self.emit("execute-file", filepath, display, time)

	@dbus.service.method(interface_name, in_signature="sayay",
	                     byte_arrays=True)
	def RelayKeysFromDisplay(self, keystring, display, notify_id):
		with uievents.using_startup_notify_id(notify_id) as time:
			self.emit("relay-keys", keystring, display, time)

	@dbus.service.method(interface_name, in_signature=None,
	                     out_signature="as",
	                     byte_arrays=True)
	def GetBoundKeys(self):
		from kupfer.ui import keybindings
		return keybindings.get_all_bound_keys()

	@dbus.service.signal(interface_name, signature="sb")
	def BoundKeyChanged(self, keystr, is_bound):
		pass

	@dbus.service.method(interface_name)
	def Quit(self):
		self.emit("quit")

# Signature: displayname, timestamp
gobject.signal_new("present", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_UINT))

# Signature: displayname, timestamp
gobject.signal_new("show-hide", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_UINT))

# Signature: text, displayname, timestamp
gobject.signal_new("put-text", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT))

# Signature: filearray, displayname, timestamp
gobject.signal_new("put-files", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_PYOBJECT, gobject.TYPE_STRING, gobject.TYPE_UINT))

# Signature: fileuri, displayname, timestamp
gobject.signal_new("execute-file", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT))

# Signature: ()
gobject.signal_new("quit", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

# Signature: keystring, displayname, timestamp
gobject.signal_new("relay-keys", Service, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN,
		(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_UINT))


