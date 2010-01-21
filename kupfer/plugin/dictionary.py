__kupfer_name__ = _("Dictionary")
__kupfer_actions__ = ("LookUp", )
__description__ = _("Look up word in dictionary")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.objects import Source, Action, TextLeaf
from kupfer import utils


class LookUp (Action):
	def __init__(self):
		Action.__init__(self, _("Look Up"))
	def activate(self, leaf):
		text = leaf.object
		utils.launch_commandline("gnome-dictionary --look-up='%s'" % text,
				_("Look Up"))
	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		text = leaf.object
		return len(text.split("\n", 1)) <= 1
	def get_description(self):
		return _("Look up word in dictionary")
	def get_icon_name(self):
		return "accessories-dictionary"
