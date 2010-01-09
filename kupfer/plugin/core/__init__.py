import gtk

from kupfer.objects import Leaf, Action, Source
from kupfer import objects
from kupfer import interface
from kupfer import pretty

__kupfer_name__ = u"Core"
# The following attributes are updated later
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_contents__ = ()
__kupfer_actions__ = (
	"SearchInside",
	"CopyToClipboard",
	)
__description__ = u"Core actions and items"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

def _is_debug():
	# Return True if Kupfer is in debug mode
	return pretty.debug

def register_subplugin(module):
	attrs = (
		"__kupfer_sources__",
		"__kupfer_actions__",
		"__kupfer_text_sources__",
		"__kupfer_contents__"
	)
	for attr in attrs:
		object_names = getattr(module, attr, ())
		globals()[attr] += object_names
		globals().update((sym, getattr(module, sym)) for sym in object_names)

from kupfer.plugin.core import contents, selection, text, internal

register_subplugin(contents)
register_subplugin(selection)
register_subplugin(text)
register_subplugin(internal)

if _is_debug():
	from kupfer.plugin.core import debug
	register_subplugin(debug)


class SearchInside (Action):
	"""
	A factory action: works on a Leaf object with content
	Return a new source with the contents of the Leaf
	"""
	def __init__(self):
		super(SearchInside, self).__init__(_("Search Contents"))

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

class CopyToClipboard (Action):
	# rank down since it applies everywhere
	rank_adjust = -2
	def __init__(self):
		Action.__init__(self, _("Copy"))
	def activate(self, leaf):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		interface.copy_to_clipboard(leaf, clip)
	def item_types(self):
		yield Leaf
	def valid_for_item(self, leaf):
		try:
			return bool(interface.get_text_representation(leaf))
		except AttributeError:
			pass
	def get_description(self):
		return _("Copy to clipboard")
	def get_icon_name(self):
		return "gtk-copy"

