from kupfer.objects import Action, Leaf
from kupfer import objects
from kupfer import pretty

__kupfer_sources__ = ()
__kupfer_actions__ = (
		"Rescan",
		"DebugInfo",
	)
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__all__ = __kupfer_sources__ + __kupfer_actions__

def _is_debug():
	# Return True if Kupfer is in debug mode
	return pretty.debug

class Rescan (Action):
	"""A source action: Rescan a source!

	This is a debug action because normal users should not need to use it;
	it is only confusing and inconsistent:

	* Sources with internal caching don't really rescan anyway.
	* Change callbacks make it redundant
	"""
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
		if _is_debug():
			yield objects.AppLeaf
			yield objects.SourceLeaf
	def valid_for_item(self, item):
		if not item.has_content():
			return False
		return not item.content_source().is_dynamic()


class DebugInfo (Action):
	""" Print debug info to terminal """
	rank_adjust = -50
	def __init__(self):
		Action.__init__(self, u"Debug Info")

	def activate(self, leaf):
		import itertools
		import StringIO
		from kupfer import qfurl
		from kupfer import uiutils

		output = StringIO.StringIO()
		def print_func(*args):
			print >>output, " ".join(unicode(a) for a in args)
			pretty.print_debug("debug", *args)

		print_func("Debug info about", leaf)
		print_func(leaf, repr(leaf))
		def get_qfurl(leaf):
			try:
				return qfurl.qfurl(leaf)
			except qfurl.QfurlError:
				pass
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
				"qfurl" : get_qfurl(leaf),
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
				"cached_items": type(src.cached_items),
				"len": isinstance(src.cached_items, list) and len(src.cached_items),
				} )
			return base

		def print_fields(fields):
			for field in sorted(fields):
				val = fields[field]
				rep = repr(val)
				print_func("%-15s:" % field, rep)
				if str(val) not in rep:
					print_func("%-15s:" % field, val)
		leafinfo = get_leaf_fields(leaf)
		print_fields(leafinfo)
		if leafinfo["content"]:
			print_func("Content ============")
			print_fields(get_source_fields(leafinfo["content"]))
		if leafinfo["content"] != leafinfo["content-alt"]:
			print_func("Content-Alt ========")
			print_fields(get_source_fields(leafinfo["content-alt"]))
		uiutils.show_text_result(output.getvalue())

	def get_description(self):
		return u"Print debug output (for interal kupfer use)"
	def get_icon_name(self):
		return "emblem-system"
	def item_types(self):
		if _is_debug():
			yield Leaf

