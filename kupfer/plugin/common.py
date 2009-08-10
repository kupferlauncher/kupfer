import gtk
import gio

from kupfer.objects import Leaf, Action, Source, RunnableLeaf
from kupfer import objects, utils, icons
from kupfer.plugin import about_support

__kupfer_name__ = _("Core")
__kupfer_sources__ = ("CommonSource", "KupferSource", )
__kupfer_contents__ = ("KupferSource", )
__kupfer_actions__ = ("SearchInside", )
__description__ = _("Core actions and miscellaneous items")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SearchInside (Action):
	"""
	A factory action: works on a Leaf object with content
	Return a new source with the contents of the Leaf
	"""
	def __init__(self):
		super(SearchInside, self).__init__(_("Search content..."))

	def is_factory(self):
		return True
	def activate(self, leaf):
		if not leaf.has_content():
			raise objects.InvalidLeafError("Must have content")
		return leaf.content_source()

	def item_types(self):
		yield Leaf
	def valid_for_item(self, leaf):
		return leaf.has_content()

	def get_description(self):
		return _("Search inside this catalog")
	def get_icon_name(self):
		return "search"

class Quit (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("Quit")
		super(Quit, self).__init__(name=name)
	def run(self):
		gtk.main_quit()
	def get_description(self):
		return _("Quit Kupfer")
	def get_icon_name(self):
		return gtk.STOCK_QUIT

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

class About (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("About Kupfer")
		super(About, self).__init__(name=name)
	def run(self):
		about_support.show_about_dialog()
	def get_description(self):
		return _("Show information about Kupfer authors and license")
	def get_icon_name(self):
		return gtk.STOCK_ABOUT

class Preferences (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("Kupfer Preferences")
		super(Preferences, self).__init__(name=name)
	def run(self):
		from kupfer import preferences
		win = preferences.GetPreferencesWindowController()
		win.show()
	def get_description(self):
		return _("Show preferences window for Kupfer")
	def get_icon_name(self):
		return gtk.STOCK_PREFERENCES

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
			SpecialLocation("trash://"),
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

class KupferSource (Source):
	def __init__(self, leaf=None, name=_("Kupfer items")):
		Source.__init__(self, name)
	def is_dynamic(self):
		return True
	def get_items(self):
		return (
			About(),
			Preferences(),
			Quit(),
		)
	def get_description(self):
		return _("Kupfer items and actions")
	def provides(self):
		yield RunnableLeaf
	def get_leaf_repr(self):
		try:
			kapp = objects.AppLeaf(item_id="kupfer.desktop")
		except objects.InvalidDataError:
			kapp = None
		return kapp
	@classmethod
	def decorates_type(cls):
		return objects.AppLeaf
	@classmethod
	def decorate_item(cls, leaf):
		if leaf.get_id() == "kupfer.desktop":
			return cls()
