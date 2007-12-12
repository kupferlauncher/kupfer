"""
This file was originally the Epiphany handler from the deskbar project

/deskbar/handlers/epiphany.py

It was downloaded from http://ftp.gnome.org/pub/GNOME/sources/deskbar-applet/

Copyright Holder: Nigel Tao  <nigel.tao@myrealbox.com>
                  Raphael Slinckx  <rslinckx@cvs.gnome.org>
                  Mikkel Kamstrup Erlandsen  <kamstrup@daimi.au.dk>

License:

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software Foundation,
    Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""


import xml.sax
from os.path import join, expanduser, exists
from gettext import gettext as _
import gtk
import deskbar, deskbar.Indexer, deskbar.Handler
from deskbar.Watcher import FileWatcher
from deskbar.BrowserMatch import get_url_host, is_preferred_browser, on_customize_search_shortcuts, on_entry_key_press, load_shortcuts
from deskbar.BrowserMatch import BrowserSmartMatch, BrowserMatch
from deskbar.defs import VERSION

def _check_requirements():
#	if deskbar.UNINSTALLED_DESKBAR:
#		return (deskbar.Handler.HANDLER_IS_HAPPY, None, None)
		
	if is_preferred_browser("epiphany"):
		return (deskbar.Handler.HANDLER_IS_HAPPY, None, None)
	else:
		return (deskbar.Handler.HANDLER_IS_NOT_APPLICABLE, "Epiphany is not your preferred browser, not using it.", None)
	
def _check_requirements_search():
	callback = lambda dialog: on_customize_search_shortcuts(smart_bookmarks, shortcuts_to_smart_bookmarks_map)
	
#	if deskbar.UNINSTALLED_DESKBAR:
#		return (deskbar.Handler.HANDLER_IS_CONFIGURABLE, "You can set shortcuts for your searches.", callback)
		
	if is_preferred_browser("epiphany"):
		return (deskbar.Handler.HANDLER_IS_CONFIGURABLE, _("You can set shortcuts for your searches."), callback)
	else:
		return (deskbar.Handler.HANDLER_IS_NOT_APPLICABLE, "Epiphany is not your preferred browser, not using it.", None)
	
HANDLERS = {
	"EpiphanyBookmarksHandler": {
		"name": _("Web Bookmarks"),
		"description": _("Open your web bookmarks by name"),
		"requirements": _check_requirements,
		"version": VERSION,
	},
	"EpiphanyHistoryHandler": {
		"name": _("Web History"),
		"description": _("Open your web history by name"),
		"requirements": _check_requirements,
		"version": VERSION,
	},
	"EpiphanySearchHandler": {
		"name": _("Web Searches"),
		"description": _("Search the web via your browser's search settings"),
		"requirements": _check_requirements_search,
		"version": VERSION,
	},
}

EPHY_BOOKMARKS_FILE = expanduser("~/.gnome2/epiphany/bookmarks.rdf")
EPHY_HISTORY_FILE   = expanduser("~/.gnome2/epiphany/ephy-history.xml")

favicon_cache = None
bookmarks = None
smart_bookmarks = None
shortcuts_to_smart_bookmarks_map = {}

class EpiphanyHandler(deskbar.Handler.Handler):
	def __init__(self, watched_file, callback, icon="stock_bookmark"):
		deskbar.Handler.Handler.__init__(self, icon)
		self.watched_file = watched_file
		self.watch_callback = callback
		
	def initialize(self):
		global favicon_cache
		if favicon_cache == None:
			favicon_cache = EpiphanyFaviconCacheParser().get_cache()
			
		if not hasattr(self, 'watcher'):
			self.watcher = FileWatcher()
			self.watcher.connect('changed', lambda watcher, f: self.watch_callback())
			
		self.watcher.add(self.watched_file)
	
	def stop(self):
		if hasattr(self, 'watcher'):
			self.watcher.remove(self.watched_file)
			del self.watcher
		
class EpiphanyBookmarksHandler(EpiphanyHandler):
	def __init__(self):
		EpiphanyHandler.__init__(self, EPHY_BOOKMARKS_FILE, lambda: self._parse_bookmarks(True))
				
	def initialize(self):
		EpiphanyHandler.initialize(self)
		self._parse_bookmarks()
		
	def _parse_bookmarks(self, force=False):
		global favicon_cache, bookmarks, smart_bookmarks
		if force or bookmarks == None:
			parser = EpiphanyBookmarksParser(self, favicon_cache)
			bookmarks = parser.get_indexer()
			smart_bookmarks = parser.get_smart_bookmarks()
			load_shortcuts(smart_bookmarks, shortcuts_to_smart_bookmarks_map)
		
	def query(self, query):
		global bookmarks
		return bookmarks.look_up(query)[:deskbar.DEFAULT_RESULTS_PER_HANDLER]

class EpiphanySearchHandler(EpiphanyBookmarksHandler):
	def __init__(self):
		EpiphanyBookmarksHandler.__init__(self)
	
	def on_key_press(self, query, shortcut):
		return on_entry_key_press(query, shortcut, shortcuts_to_smart_bookmarks_map)
	
	def query(self, query):
		# if one of the smart bookmarks' shortcuts matches as a prefix,
		# then only return that bookmark
		x = query.find(" ")
		if x != -1:
			prefix = query[:x]
			try:
				b = shortcuts_to_smart_bookmarks_map[prefix]
				text = query[x+1:]
				return [BrowserSmartMatch(b.get_handler(), b.name, b.url, prefix, b, icon=b.icon)]
			except KeyError:
				# Probably from the b = ... line.  Getting here
				# means that there is no such shortcut.
				pass
		
		return smart_bookmarks
		
class EpiphanyHistoryHandler(EpiphanyHandler):
	def __init__(self):
		EpiphanyHandler.__init__(self, EPHY_HISTORY_FILE, self._parse_history, "epiphany-history.png")
		self._history = None
		
	def initialize(self):
		EpiphanyHandler.initialize(self)
		self._parse_history()
		
	def _parse_history(self):
		global favicon_cache
		self._history = EpiphanyHistoryParser(self, favicon_cache).get_indexer()
			
	def query(self, query):
		return self._history.look_up(query)[:deskbar.DEFAULT_RESULTS_PER_HANDLER]
		
class EpiphanyBookmarksParser(xml.sax.ContentHandler):
	def __init__(self, handler, cache):
		xml.sax.ContentHandler.__init__(self)
		
		self.handler = handler
		
		self.chars = ""
		self.title = None
		self.href = None
		self.smarthref = None
		
		self._indexer = deskbar.Indexer.Indexer()
		self._smart_bookmarks = []
		self._cache = cache;
		
		self._index_bookmarks()
	
	def get_indexer(self):
		"""
		Returns a completed indexer with the contents of bookmark file
		"""
		return self._indexer
	
	def get_smart_bookmarks(self):
		"""
		Return a list of EpiphanySmartMatch instances representing smart bookmarks
		"""
		return self._smart_bookmarks
		
	def _index_bookmarks(self):
		if exists(EPHY_BOOKMARKS_FILE):
			parser = xml.sax.make_parser()
			parser.setContentHandler(self)
			parser.parse(EPHY_BOOKMARKS_FILE)
	
	def characters(self, chars):
		self.chars = self.chars + chars
		
	def startElement(self, name, attrs):
		self.chars = ""
		if name == "item":
			self.title = None
			self.href = None
			self.smarthref = None

	def endElement(self, name):
		if name == "title":
			self.title = self.chars.encode('utf8')
		elif name == "link":
			self.href = self.chars.encode('utf8')
		elif name == "ephy:smartlink":
			self.smarthref = self.chars.encode('utf8')
		elif name == "item":
			if self.href.startswith("javascript:"):
				return
			
			icon = None
			host = get_url_host(self.href)
			if host in self._cache:
				icon = self._cache[host]

			bookmark = BrowserMatch(self.handler, self.title, self.href, icon=icon)
			if self.smarthref != None:
				bookmark = BrowserSmartMatch(self.handler, self.title, self.smarthref, icon=icon, bookmark=bookmark)
				self._smart_bookmarks.append(bookmark)
			else:
				self._indexer.add("%s %s" % (self.title, self.href), bookmark)

class EpiphanyFaviconCacheParser(xml.sax.ContentHandler):
	def __init__(self):
		xml.sax.ContentHandler.__init__(self)
		self.ephy_dir = expanduser("~/.gnome2/epiphany")
		self.filename = join(self.ephy_dir, "ephy-favicon-cache.xml")
		
		self.cache = None
		
		self.chars = ""
		self.url = None
		self.name = None
	
	def get_cache(self):
		"""
		Returns a dictionary of (host, favicon path) entries where
		  host is the hostname, like google.com (without www)
		  favicon path is the on-disk path to the favicon image file.
		"""
		if self.cache != None:
			return self.cache
		
		self.cache = {}
		if exists(self.filename):
			parser = xml.sax.make_parser()
			parser.setContentHandler(self)
			parser.parse(self.filename)
			
		return self.cache
	
	def characters(self, chars):
		self.chars = self.chars + chars
		
	def startElement(self, name, attrs):
		self.chars = ""
		if name == "property" and attrs['id'] == "2":
			self.url = None
		if name == "property" and attrs['id'] == "3":
			self.name = None

	def endElement(self, name):
		if name == "property":
			if self.url == None:
				self.url = self.chars
			elif self.name == None:
				self.name = self.chars
		elif name == "node":
			# Splithost requires //xxxx[:port]/xxxx, so we remove "http:"
			host = get_url_host(self.url)
			self.cache[host] = join(self.ephy_dir, "favicon_cache", self.name.encode('utf8'))



class EpiphanyHistoryParser(xml.sax.ContentHandler):
	def __init__(self, handler, cache):
		xml.sax.ContentHandler.__init__(self)

		self.handler = handler;
		self._cache = cache;
		
		self.url = None
		self.title = None
		self.icon = None
		self._id = None;
	
		self._indexer = deskbar.Indexer.Indexer()

		self._index_history();

	def get_indexer(self):
		"""
		Returns a completed indexer with the contents of the history file
		"""
		return self._indexer;

	def _index_history(self):
		if exists(EPHY_HISTORY_FILE):
			parser = xml.sax.make_parser()
			parser.setContentHandler(self)
			try:
				parser.parse(EPHY_HISTORY_FILE)
			except Exception, e:
				print "Couldn't parse epiphany history file:", e

	
	def characters(self, chars):
		self.chars = self.chars + chars
		
	def startElement(self, name, attrs):
		self.chars = ""
		if name == "property":
			self._id = attrs['id']

		if name == "node":
			self.title = None
			self.url = None
			self.icon = None

	def endElement(self, name):
		if name == "property":
			if self._id == "2":
				self.title = self.chars.encode('utf8')
			elif self._id == "3":
				self.url = self.chars.encode('utf8')
			elif self._id == "9":
				self.icon = self.chars.encode('utf8')
		elif name == "node":
			icon = None
			if self.icon in self._cache:
				icon = self._cache[self.icon]

			item = BrowserMatch(self.handler, self.title, self.url, True, icon=icon)
			self._indexer.add("%s %s" % (self.title, self.url), item)
