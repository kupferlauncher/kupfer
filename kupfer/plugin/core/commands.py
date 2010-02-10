__kupfer_actions__ = ("SaveToFile", )

import os

from kupfer.objects import Action, FileLeaf, TextLeaf, TextSource
from kupfer.obj.compose import ComposedLeaf
from kupfer import execfile


class SaveToFile (Action):
	def __init__(self):
		Action.__init__(self, _("Save As..."))

	def has_result(self):
		return True

	def activate(self, obj, iobj):
		execfile.save_to_file(obj, iobj.object)
		return FileLeaf(os.path.abspath(iobj.object))

	def item_types(self):
		yield ComposedLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf
