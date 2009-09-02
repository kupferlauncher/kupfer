from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.objects import UrlLeaf
from kupfer import plugin_support

__kupfer_name__ = _("Epiphany Bookmarks")
__kupfer_sources__ = ("EpiphanySource", )
__kupfer_contents__ = ("EpiphanySource", )
__description__ = _("Index of Epiphany bookmarks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)

class EpiphanySource (AppLeafContentMixin, Source):
	appleaf_content_id = "epiphany"
	def __init__(self):
		super(EpiphanySource, self).__init__(_("Epiphany Bookmarks"))
	
	def get_items(self):
		from epiphany_support import EpiphanyBookmarksParser
		parser = EpiphanyBookmarksParser()
		bookmarks = parser.get_items()
		return (UrlLeaf(href, title) for title, href in bookmarks)

	def get_description(self):
		return _("Index of Epiphany bookmarks")

	def get_icon_name(self):
		return "web-browser"
	def provides(self):
		yield UrlLeaf

