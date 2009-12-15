import gtk

from kupfer.objects import Leaf, Action, Source
from kupfer import objects

__kupfer_name__ = u"Core"
__kupfer_sources__ = ()   # Updated later
__kupfer_actions__ = (    # Updated later
	"SearchInside",
	)
__description__ = u"Core actions and items"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

def _register_subplugin(module):
	global __kupfer_sources__
	global __kupfer_actions__
	__kupfer_sources__ += module.__kupfer_sources__
	__kupfer_actions__ += module.__kupfer_actions__
	globals().update((attr, getattr(module, attr)) for attr in module.__all__)

from kupfer.plugin.core import contents, debug
_register_subplugin(contents)
_register_subplugin(debug)

class SearchInside (Action):
	"""
	A factory action: works on a Leaf object with content
	Return a new source with the contents of the Leaf
	"""
	def __init__(self):
		super(SearchInside, self).__init__(_("Search Content..."))

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
