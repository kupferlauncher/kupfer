from __future__ import absolute_import
# TRANS: "Glob" is the matching files like a shell with "*.py" etc.
__kupfer_name__ = _("Glob")
__kupfer_actions__ = ("Glob",)
__description__ = ""
__version__ = ""
__author__ = "Ulrik"

import fnmatch
import re

from kupfer.objects import Action, TextLeaf, Source, TextSource, Leaf
from kupfer import utils, pretty

class ObjSource (Source):
	def __init__(self, files):
		Source.__init__(self, _("Glob Result"))
		self.files = files
	def get_items(self):
		return self.files
	def should_sort_lexically(self):
		return True
	def provides(self):
		yield Leaf

class Glob (Action):
	def __init__(self):
		Action.__init__(self, _("Glob"))

	def activate(self, obj, iobj):
		return self.activate_multiple((obj,), (iobj, ))

	def activate_multiple(self, objects, iobjects):
		## Do case-insentive matching
		paths = []
		for iobj in iobjects:
			glob = iobj.object
			pat = fnmatch.translate(glob)
			for obj in objects:
				for content in obj.content_source().get_leaves():
					if re.match(pat, unicode(content), flags=re.I):
						paths.append(content)
		return ObjSource(paths)

	def is_factory(self):
		return True
	def item_types(self):
		yield Leaf
	def valid_for_item(self, item):
		return item.has_content()
	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf
	def object_source(self, for_item=None):
		return TextSource()
	def valid_object(self, iobj, for_item):
		return (u'*' in iobj.object) or (u'?' in iobj.object)

