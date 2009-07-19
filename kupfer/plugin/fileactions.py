import gio
import os

from kupfer.objects import Action, FileLeaf
from kupfer import utils


__kupfer_name__ = _("File actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("Trash", "MoveTo", "UnpackHere", "CreateArchive")
__description__ = _("More file actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Trash (Action):
	def __init__(self):
		Action.__init__(self, _("Move to trash"))

	def activate(self, leaf):
		gfile = gio.File(leaf.object)
		gfile.trash()
	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def get_description(self):
		return _("Move this file to trash")
	def get_icon_name(self):
		return "user-trash-full"
	def item_types(self):
		yield FileLeaf

class MoveTo (Action):
	def __init__(self):
		Action.__init__(self, _("Move to..."))
	def activate(self, leaf, obj):
		raise NotImplementedError("Want to move %s to %s" % (leaf, obj))

	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def requires_object(self):
		return True

	def item_types(self):
		yield FileLeaf
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item=None):
		if not obj.is_dir():
			return False
		spath = os.path.normpath(for_item.object)
		dpath = os.path.normpath(obj.object)
		if not os.access(dpath, os.R_OK | os.W_OK | os.X_OK):
			return False
		cpfx = os.path.commonprefix((spath, dpath))
		if os.path.samefile(dpath, spath) or (cpfx == spath):
			return False
		return True
	def get_description(self):
		return _("Move file to new location")

class UnpackHere (Action):
	def __init__(self):
		Action.__init__(self, _("Unpack archive"))
	def activate(self, leaf):
		utils.launch_commandline("file-roller --extract-here %s" % leaf.object)

	def valid_for_item(self, item):
		tail, ext = os.path.splitext(item.object)
		# FIXME: Make this detection smarter
		return ext.lower() in (".rar", ".7z", ".zip", ".gz")

	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("Unpack compressed archive here")

class CreateArchive (Action):
	def __init__(self):
		Action.__init__(self, _("Create archive"))
	def activate(self, leaf):
		utils.launch_commandline("file-roller --add %s" % leaf.object)

	def valid_for_item(self, item):
		# FIXME: Only for directories right now
		return item.is_dir()
	def item_types(self):
		yield FileLeaf
	def get_description(self):
		return _("create a compressed archive from folder")
