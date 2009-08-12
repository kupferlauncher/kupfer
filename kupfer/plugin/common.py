import gtk
import gio

from kupfer.objects import Leaf, Action, Source, RunnableLeaf
from kupfer import objects, utils, icons
from kupfer.plugin import about_support

__kupfer_name__ = _("Common")
__kupfer_sources__ = ("CommonSource", )
__description__ = _("Miscellaneous items")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Logout (RunnableLeaf):
	"""Log out from desktop"""
	def __init__(self, name=None):
		if not name: name = _("Log out...")
		super(Logout, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-panel-logout", _("Log out..."))
		if not ret:
			utils.launch_commandline("gnome-session-save --kill", _("Log out..."))
	def get_description(self):
		return _("Log out or change user")
	def get_icon_name(self):
		return "system-log-out"

class Shutdown (RunnableLeaf):
	"""Shutdown computer or reboot"""
	def __init__(self, name=None):
		if not name: name = _("Shut down...")
		super(Shutdown, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-panel-logout --shutdown", _("Shut down..."))
		if not ret:
			utils.launch_commandline("gnome-session-save --kill", _("Shut down..."))

	def get_description(self):
		return _("Shut down, restart or suspend computer")
	def get_icon_name(self):
		return "system-shutdown"

class LockScreen (RunnableLeaf):
	"""Lock screen"""
	def __init__(self, name=None):
		if not name: name = _("Lock screen")
		super(LockScreen, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-screensaver-command --lock", _("Lock screen"))
	def get_description(self):
		return _("Enable screensaver and lock")
	def get_icon_name(self):
		return "system-lock-screen"

class SpecialLocation (objects.Leaf):
	""" Base class for Special locations (in GIO/GVFS),
	such as trash:/// Here we assume they are all "directories"
	"""
	def __init__(self, location, name=None, description=None, icon_name=None):
		"""Special location with @location and
		@name. If unset, we find @name from filesystem
		@description is Leaf description"""
		gfile = gio.File(location)
		info = gfile.query_info(gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME)
		name = (info.get_attribute_string(gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME) or location)
		Leaf.__init__(self, location, name)
		self.description = description
		self.icon_name = icon_name
	def get_actions(self):
		yield objects.OpenDirectory()
	def get_description(self):
		return self.description or self.object
	def get_gicon(self):
		# Get icon
		return icons.get_gicon_for_file(self.object)
	def get_icon_name(self):
		return "folder"

class Trash (SpecialLocation):
	def __init__(self, name=None):
		SpecialLocation.__init__(self, "trash://", name=name)
	def get_description(self):
		gfile = gio.File(self.object)
		info = gfile.query_info(gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT)
		item_count = info.get_attribute_uint32(gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT)
		if not item_count:
			return _("Trash is empty")
		# proper translation of plural
		return ngettext("Trash contains one file",
			"Trash contains %(num)s files", item_count) % {"num": item_count}

class CommonSource (Source):
	def __init__(self, name=_("Special items")):
		super(CommonSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_items(self):
		return (
			# These seem to be included in applications now..
			#SpecialLocation("computer://", description=_("Browse local disks and mounts")),
			#SpecialLocation("burn://"),
			Trash(),
			Logout(),
			LockScreen(),
			Shutdown(),
		)
	def get_description(self):
		return _("Items and special actions")
	def get_icon_name(self):
		return "applications-other"
	def provides(self):
		yield SpecialLocation
		yield RunnableLeaf
