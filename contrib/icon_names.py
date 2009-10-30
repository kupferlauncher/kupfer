"""
A quick hack to search the icons of the `Icon Naming Specification`__, shown
as available on the current system.

__ http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html
"""

import urllib
from xml.etree import cElementTree as ET

from kupfer.objects import Leaf, Action, Source, RunnableLeaf
from kupfer import uiutils
from kupfer import plugin_support

__kupfer_name__ = _("Icon Names")
__kupfer_sources__ = ("IconNameSource", )
__description__ = _("Browse the icons of the Icon Naming Specification")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)


ICON_SPEC_ADDRESS = "http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-0.8.90.xml"

class ShowDescription(Action):
	def __init__(self):
		Action.__init__(self, _("Show Full Description"))
	def activate(self, leaf):
		uiutils.show_large_type(leaf.description)

class IconName (Leaf):
	def __init__(self, obj, desc, category):
		Leaf.__init__(self, obj, obj)
		self.description = desc
		self.name_aliases.add(desc.splitlines()[0])
	def get_actions(self):
		yield ShowDescription()
	def get_description(self):
		return self.description.splitlines()[0]
	def get_icon_name(self):
		return self.object

class IconNameSource (Source):
	def __init__(self):
		return Source.__init__(self, _("Icon Names"))
	def get_items(self):
		parsed = ET.parse(urllib.urlopen(ICON_SPEC_ADDRESS))
		root = parsed.getroot()

		icon_names = {}
		def first(lst):
			return iter(lst).next()

		def flatten(tag):
			"""return text of @tag and its immediate children"""
			return tag.text + "".join(c.text+c.tail for c in tag.getchildren())

		names = first(s for s in root.findall("sect1") if s.get("id") == "names")
		for table in names.findall("table"):
			category_name = table.get("id")
			rows = table.find("tgroup").find("tbody")
			for row in rows:
				icon_names.setdefault(category_name, []).append(
						tuple(flatten(e).strip() for e in row.findall("entry")))

		for category in icon_names:
			for name, desc in icon_names[category]:
				yield IconName(name, desc, category)

	def get_icon_name(self):
		return "emblem-photos"

