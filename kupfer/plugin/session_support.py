import gio

from kupfer.objects import Leaf, Action, Source, RunnableLeaf
from kupfer import objects, utils, icons, pretty

'''
Common objects for session_* plugins.
'''

__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


def launch_commandline_with_fallbacks(commands, print_error=True):
	"""Try the sequence of @commands with utils.launch_commandline,
	and return with the first successful command.
	return False if no command is successful and log an error
	"""
	for command in commands:
		ret = utils.launch_commandline(command)
		if ret: return ret
	pretty.print_error(__name__, "Unable to run command(s)", commands)
	return False

class Logout (RunnableLeaf):
	"""Log out from desktop"""
	def __init__(self, commands, name=None):
		if not name: name = _("Log Out...")
		super(Logout, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)
	def get_description(self):
		return _("Log out or change user")
	def get_icon_name(self):
		return "system-log-out"

class Shutdown (RunnableLeaf):
	"""Shutdown computer or reboot"""
	def __init__(self, commands, name=None):
		if not name: name = _("Shut Down...")
		super(Shutdown, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)

	def get_description(self):
		return _("Shut down, restart or suspend computer")
	def get_icon_name(self):
		return "system-shutdown"

class LockScreen (RunnableLeaf):
	"""Lock screen"""
	def __init__(self, commands, name=None):
		if not name: name = _("Lock Screen")
		super(LockScreen, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)
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

class RestoreTrashedFile (Action):
	def __init__(self):
		Action.__init__(self, _("Restore"))

	def activate(self, leaf):
		orig_path = leaf.get_orig_path()
		if not orig_path:
			return
		orig_gfile = gio.File(orig_path)
		cur_gfile = leaf.get_gfile()
		if orig_gfile.query_exists():
			raise IOError("Target file exists at %s" % orig_gfile.get_path())
		pretty.print_debug(__name__, "Move %s to %s" % (cur_gfile, orig_gfile))
		ret = cur_gfile.move(orig_gfile)
		pretty.print_debug(__name__, "Move ret=%s" % (ret, ))

	def get_description(self):
		return _("Move file back to original location")
	def get_icon_name(self):
		return "gtk-undo-ltr"

class TrashFile (Leaf):
	"""A file in the trash. Represented object is a file info object"""
	def __init__(self, trash_uri, info):
		name = info.get_display_name()
		Leaf.__init__(self, info, name)
		self._trash_uri = trash_uri
	def get_actions(self):
		if self.get_orig_path():
			yield RestoreTrashedFile()
	def get_gfile(self):
		cur_gfile = gio.File(self._trash_uri).get_child(self.object.get_name())
		return cur_gfile
	def get_orig_path(self):
		try:
			orig_path = self.object.get_attribute_byte_string("trash::orig-path")
			return orig_path
		except AttributeError:
			pass
		return None

	def is_valid(self):
		return self.get_gfile().query_exists()

	def get_description(self):
		orig_path = self.get_orig_path()
		return utils.get_display_path_for_bytestring(orig_path) if orig_path \
				else None
	def get_gicon(self):
		return self.object.get_icon()
	def get_icon_name(self):
		return "gtk-file"

class TrashContentSource (Source):
	def __init__(self, trash_uri, name):
		Source.__init__(self, name)
		self._trash_uri = trash_uri

	def is_dynamic(self):
		return True
	def get_items(self):
		gfile = gio.File(self._trash_uri)
		enumerator = gfile.enumerate_children("standard::*,trash::*")
		for info in enumerator:
			yield TrashFile(self._trash_uri, info)
	def should_sort_lexically(self):
		return True
	def get_gicon(self):
		return icons.get_gicon_for_file(self._trash_uri)

class Trash (SpecialLocation):
	def __init__(self, trash_uri, name=None):
		SpecialLocation.__init__(self, trash_uri, name=name)

	def has_content(self):
		return self.get_item_count()
	def content_source(self, alternate=False):
		return TrashContentSource(self._uri, name=unicode(self))

	def get_item_count(self):
		gfile = gio.File(self.object)
		info = gfile.query_info(gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT)
		return info.get_attribute_uint32(gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT)

	def get_description(self):
		item_count = self.get_item_count()
		if not item_count:
			return _("Trash is empty")
		# proper translation of plural
		return ngettext("Trash contains one file",
			"Trash contains %(num)s files", item_count) % {"num": item_count}

class CommonSource (Source):
	def __init__(self, name=_("Special Items")):
		super(CommonSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_description(self):
		return _("Items and special actions")
	def get_icon_name(self):
		return "applications-other"
	def provides(self):
		yield SpecialLocation
		yield RunnableLeaf
