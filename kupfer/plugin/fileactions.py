import gio
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
	def get_description(self):
		return _("Move this file to trash")
	def get_icon_name(self):
		return "user-trash-full"

class MoveTo (Action):
	def __init__(self):
		Action.__init__(self, _("Move to..."))
	def activate(self, leaf, obj):
		print "Want to move", leaf, "to", obj

	def requires_object(self):
		return True

	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj):
		return obj.is_dir()

