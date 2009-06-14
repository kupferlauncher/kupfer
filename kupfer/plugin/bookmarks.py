from kupfer.objects import Leaf, Action, Source
from kupfer.objects import UrlLeaf

class BookmarksSource (Source):
	def __init__(self):
		super(BookmarksSource, self).__init__(_("Firefox Bookmarks"))
	
	def get_items(self):
		from firefox_support import get_firefox_home_file, get_bookmarks
		bookmarks = get_bookmarks(get_firefox_home_file("bookmarks.html"))
		return (UrlLeaf(book["href"], book["title"][:40]) for book in bookmarks)

	def get_icon_name(self):
		return "web-browser"

class EpiphanySource (Source):
	def __init__(self):
		super(EpiphanySource, self).__init__(_("Epiphany Bookmarks"))
	
	def get_items(self):
		from epiphany_support import EpiphanyBookmarksParser
		parser = EpiphanyBookmarksParser()
		bookmarks = parser.get_items()
		return (UrlLeaf(href, title) for title, href in bookmarks)

	def get_icon_name(self):
		return "web-browser"

