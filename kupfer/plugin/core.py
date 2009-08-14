import gtk

from kupfer.objects import Leaf, Action, Source, RunnableLeaf, AppLeafContentMixin
from kupfer import objects, utils, icons, pretty
from kupfer.plugin import about_support

__kupfer_name__ = u"Core"
__kupfer_sources__ = ("KupferSource", )
__kupfer_contents__ = ("KupferSource", )
__kupfer_actions__ = (
	"SearchInside",
	"Rescan",
	"DebugInfo",
	)
__description__ = u"Core actions and items"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

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

class Rescan (Action):
	""" A source action: Rescan a source!  """
	rank_adjust = -5
	def __init__(self):
		Action.__init__(self, _("Rescan"))

	def activate(self, leaf):
		if not leaf.has_content():
			raise objects.InvalidLeafError("Must have content")
		source = leaf.content_source()
		source.get_leaves(force_update=True)

	def get_description(self):
		return _("Force reindex of this source")
	def get_icon_name(self):
		return "gtk-refresh"

	def item_types(self):
		yield objects.AppLeaf
		yield objects.SourceLeaf
	def valid_for_item(self, item):
		if not item.has_content():
			return False
		return not item.content_source().is_dynamic()

class DebugInfo (Action, pretty.OutputMixin):
	"""
	Print debug info to terminal
	"""
	rank_adjust = -50
	def __init__(self):
		Action.__init__(self, u"Debug Info")

	def activate(self, leaf):
		import itertools
		print_func = lambda *args : pretty.print_debug("debug", *args)
		print_func("Debug info about", leaf)
		print_func(leaf, repr(leaf))
		def get_object_fields(leaf):
			return {
				"repr" : leaf,
				"description": leaf.get_description(),
				"thumb" : leaf.get_thumbnail(32, 32),
				"gicon" : leaf.get_gicon(),
				"icon" : leaf.get_icon(),
				"icon-name": leaf.get_icon_name(),
				"type" : type(leaf),
				"module" : leaf.__module__,
				"aliases" : getattr(leaf, "name_aliases", None),
				}
		def get_leaf_fields(leaf):
			base = get_object_fields(leaf)
			base.update( {
				"object" : leaf.object,
				"object-type" : type(leaf.object),
				"content" : leaf.content_source(),
				"content-alt" : leaf.content_source(alternate=True),
				"builtin-actions": list(leaf.get_actions()),
				} )
			return base
		def get_source_fields(src):
			base = get_object_fields(src)
			base.update({
				"dynamic" : src.is_dynamic(),
				"sort" : src.should_sort_lexically(),
				"parent" : src.get_parent(),
				"leaf" : src.get_leaf_repr(),
				"provides" : list(src.provides()),
				} )
			return base

		def print_fields(fields):
			for field in sorted(fields):
				val = fields[field]
				rep = repr(val)
				print_func("%-10s:" % field, rep)
				if str(val) not in rep:
					print_func("%-10s:" % field, val)
		leafinfo = get_leaf_fields(leaf)
		print_fields(leafinfo)
		if leafinfo["content"]:
			print_func("Content ============")
			print_fields(get_source_fields(leafinfo["content"]))
		if leafinfo["content"] != leafinfo["content-alt"]:
			print_func("Content-Alt ========")
			print_fields(get_source_fields(leafinfo["content-alt"]))

	def get_description(self):
		return u"Print debug output (for interal kupfer use)"
	def get_icon_name(self):
		return "emblem-system"
	def item_types(self):
		if pretty.debug:
			yield Leaf

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

class KupferSource (AppLeafContentMixin, Source):
	appleaf_content_id = "kupfer.desktop"
	def __init__(self, name=_("Kupfer")):
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
	def get_icon_name(self):
		return "search"
	def provides(self):
		yield RunnableLeaf
