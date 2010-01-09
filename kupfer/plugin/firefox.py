import os

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import plugin_support

__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__description__ = _("Index of Firefox bookmarks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)

class BookmarksSource (AppLeafContentMixin, Source):
	appleaf_content_id = ("firefox", "iceweasel")
	def __init__(self):
		super(BookmarksSource, self).__init__(_("Firefox Bookmarks"))
	
	def _get_ffx3_items(self, fpath):
		"""Parse Firefox' .json bookmarks backups"""
		from firefox3_support import get_bookmarks
		self.output_debug("Parsing", fpath)
		bookmarks = get_bookmarks(fpath)
		for book in bookmarks:
			yield UrlLeaf(book["uri"], book["title"])

	def _get_ffx2_items(self, fpath):
		"""Parse Firefox' bookmarks.html"""
		from firefox_support import get_bookmarks
		self.output_debug("Parsing", fpath)
		bookmarks = get_bookmarks(fpath)
		for book in bookmarks:
			yield UrlLeaf(book["href"], book["title"])

	def get_items(self):
		import firefox_support
		dirloc = firefox_support.get_firefox_home_file("bookmarkbackups")
		fpath = None
		if dirloc:
			files = os.listdir(dirloc)
			if files:
				latest_file = (files.sort() or files)[-1]
				fpath = os.path.join(dirloc, latest_file)

		if fpath and os.path.splitext(fpath)[-1].lower() == ".json":
			try:
				return list(self._get_ffx3_items(fpath))
			except Exception, exc:
				# Catch JSON parse errors
				# different exception for cjson and json
				self.output_error(exc)

		fpath = firefox_support.get_firefox_home_file("bookmarks.html")
		if fpath:
			return self._get_ffx2_items(fpath)

		self.output_error("No firefox bookmarks file found")
		return []

	def get_description(self):
		return _("Index of Firefox bookmarks")
	def get_gicon(self):
		return self.get_leaf_repr() and self.get_leaf_repr().get_gicon()
	def get_icon_name(self):
		return "web-browser"
	def provides(self):
		yield UrlLeaf
