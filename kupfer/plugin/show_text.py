
__kupfer_name__ = _("Show Text")
__kupfer_actions__ = (
		"ShowText",
		"LargeType",
	)
__description__ = _("Display text in a window")
__version__ = "0.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.objects import Action
from kupfer.objects import TextLeaf
from kupfer import icons, kupferstring, uiutils
from kupfer import plugin_support

__kupfer_plugin_category__ = plugin_support.CATEGORY_KUPFER

class ShowText (Action):
	def __init__(self):
		Action.__init__(self, _("Show Text"))

	def activate(self, leaf):
		uiutils.show_text_result(leaf.object, title=_("Show Text"))

	def item_types(self):
		yield TextLeaf

	def get_description(self):
		return _("Display text in a window")
	def get_icon_name(self):
		return "gtk-bold"

class LargeType (Action):
	def __init__(self):
		Action.__init__(self, _("Large Type"))

	def activate(self, leaf):
		uiutils.show_large_type(leaf.object)

	def item_types(self):
		yield TextLeaf

	def get_description(self):
		return _("Display text in a window")
	def get_gicon(self):
		return icons.ComposedIcon("gtk-bold", "zoom-in")
	def get_icon_name(self):
		return "gtk-bold"

