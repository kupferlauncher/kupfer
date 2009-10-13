import os

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import (TextLeaf, ConstructFileLeaf, FileLeaf)
from kupfer import icons, plugin_support


__kupfer_name__ = _("Locate Files")
__kupfer_actions__ = (
		"Locate",
	)
__description__ = _("Search filesystem using locate")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"
__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "ignore_case",
		"label": _("Ignore case distinctions when searching files"),
		"type": bool,
		"value": True,
	},
)

class Locate (Action):
	def __init__(self):
		Action.__init__(self, _("Locate Files"))

	def is_factory(self):
		return True
	def activate(self, leaf):
		return LocateQuerySource(leaf.object)
	def item_types(self):
		yield TextLeaf

	def get_description(self):
		return _("Search filesystem using locate")
	def get_gicon(self):
		return icons.ComposedIcon("gnome-terminal", "gtk-find")
	def get_icon_name(self):
		return "gtk-find"

class LocateQuerySource (Source):
	def __init__(self, query):
		Source.__init__(self, name=_('Results for "%s"') % query)
		self.query = query
		self.max_items = 500

	def get_items(self):
		ignore_case = '--ignore-case' if __kupfer_settings__["ignore_case"] else ''
		command = "locate --quiet --null --limit %d %s '%s'" % \
				(self.max_items, ignore_case, self.query)
		locate_output = os.popen(command).read()
		files = locate_output.split("\x00")[:-1]
		for filestr in files:
			yield ConstructFileLeaf(filestr)
		if len(files) == self.max_items:
			self.output_debug("Found maximum number of files for", self.query)

	def get_gicon(self):
		return icons.ComposedIcon("gnome-terminal", "gtk-find")
	def get_icon_name(self):
		return "gtk-find"
