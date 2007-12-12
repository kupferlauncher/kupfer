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

EPHY_BOOKMARKS_FILE = expanduser("~/.gnome2/epiphany/bookmarks.rdf")
EPHY_HISTORY_FILE   = expanduser("~/.gnome2/epiphany/ephy-history.xml")

favicon_cache = None
bookmarks = None
smart_bookmarks = None
shortcuts_to_smart_bookmarks_map = {}

		
class EpiphanyBookmarksParser(xml.sax.ContentHandler):
	def __init__(self):
		xml.sax.ContentHandler.__init__(self)
		
		self.chars = ""
		self.title = None
		self.href = None
		
		self._indexer = set() 
	
	def get_items(self):
		"""
		Returns a completed indexer with the contents of bookmark file
		"""
		if not self._indexer:
			self._index_bookmarks()
		return self._indexer

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

	def endElement(self, name):
		if name == "title":
			self.title = self.chars.encode('utf8')
		elif name == "link":
			self.href = self.chars.encode('utf8')
		elif name == "item":
			if self.href.startswith("javascript:"):
				return
			else:
				# save bookmark
				if self.href:
					self._indexer.add((self.title, self.href))

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
