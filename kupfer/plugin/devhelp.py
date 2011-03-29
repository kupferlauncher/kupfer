__kupfer_name__ = _("Devhelp")
__kupfer_actions__ = ("LookUp", )
__description__ = _("Search in Devhelp")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.objects import Action, TextLeaf
from kupfer import utils


class LookUp (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Devhelp"))
	def activate(self, leaf):
		text = leaf.object
		utils.spawn_async(['devhelp', '--search=%s' % text])
	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		text = leaf.object
		return len(text.splitlines()) <= 1
	def get_description(self):
		return None
	def get_icon_name(self):
		return "devhelp"
