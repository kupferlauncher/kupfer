import gio
import os

from kupfer.objects import Action
from kupfer.objects import FileLeaf, ActionDecorator
from kupfer import utils


__kupfer_name__ = _("File actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_action_decorator__ = ("Decorator", )
__description__ = _("More file actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Decorator (ActionDecorator):
	def applies_to(self):
		yield FileLeaf
	def get_actions(self, leaf=None):
		yield Trash()
		yield MoveTo()

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

class MoveTo (Action):
	def __init__(self):
		Action.__init__(self, _("Move to..."))
	def activate(self, leaf, obj):
		raise NotImplementedError("Want to move %s to %s" % (leaf, obj))

	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def requires_object(self):
		return True

	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item=None):
		if not obj.is_dir():
			return False
		spath = os.path.normpath(for_item.object)
		dpath = os.path.normpath(obj.object)
		cpfx = os.path.commonprefix((spath, dpath))
		if os.path.samefile(obj.object, for_item.object) or (cpfx == spath):
			return False
		return True

