from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.objects import UrlLeaf

__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_contents__ = ("BookmarksSource", )
__description__ = _("Index of Firefox bookmarks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class BookmarksSource (AppLeafContentMixin, Source):
	appleaf_content_id = ("firefox", "iceweasel")
	def __init__(self):
		super(BookmarksSource, self).__init__(_("Firefox Bookmarks"))
	
	def get_items(self):
		from firefox_support import get_firefox_home_file, get_bookmarks
		bookmarks = get_bookmarks(get_firefox_home_file("bookmarks.html"))
		return (UrlLeaf(book["href"], book["title"][:40]) for book in bookmarks)

	def get_description(self):
		return _("Index of Firefox bookmarks")
	def get_gicon(self):
		return self.get_leaf_repr() and self.get_leaf_repr().get_gicon()
	def get_icon_name(self):
		return "web-browser"
	def provides(self):
		yield UrlLeaf
