# -*- coding: UTF-8 -*-

"""
Original file much thanks to
http://www.kylo.net/deli.py.txt

Modifications released under GPL v2 (or any later)
Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
"""
import os

from ConfigParser import RawConfigParser
from HTMLParser import HTMLParser
 
def get_firefox_home_file(needed_file):
    for firefox_dir in (os.path.expanduser(p) for p in
			("~/.mozilla/firefox-3.5/", "~/.mozilla/firefox/")):
        if os.path.exists(firefox_dir):
            break
    else:
        # no break
        return None
    # here we leak firefox_dir
    config = RawConfigParser({"Default" : 0})
    config.read(os.path.join(firefox_dir, "profiles.ini"))
    path = None

    for section in config.sections():
        if config.has_option(section, "Default") and config.get(section, "Default") == "1":
            path = config.get (section, "Path")
            break
        elif path == None and config.has_option(section, "Path"):
            path = config.get (section, "Path")
        
    if path == None:
        return ""

    if path.startswith("/"):
        return os.path.join(path, needed_file)

    return os.path.join(firefox_dir, path, needed_file)


class BookmarksParser(HTMLParser):

	def __init__(self):
		# this is python: explicitly invoke base class constructor
		HTMLParser.__init__(self)
		self.inH3		= False
		self.inA		 = False
		self.tagCount	= 0
		self.tags		= []
		self.currentTag  = ""
		self.href		= ""
		self.description = ""
		self.ignore	  = ""
		
		self.debug = False
		self.all_items = []

	def setBaseTag(self, baseTag):
		self.tags.append(baseTag)

	def setIgnoreUrls(self, ignore):
		self.ignore = ignore
		
	# remove white space
	# remove apostrophes, quote, double-quotes, colons, commas
	def normalizeText(self, text):
		text = text.replace('\'', '')
		text = text.replace('"', '')
		text = text.replace('`', '')
		text = text.replace(':', '')
		text = text.replace(',', '')
		text = text.replace(' ', '')
		text = text.replace('	', '')
		return text

	def handle_starttag(self, tag, attrs):
		if tag == "a":
			self.inA = True
			for attr in attrs:
				if attr[0] == "href":
					self.href = attr[1]
					

		if tag == "h3":
			self.inH3 = True
			self.tagCount += 1

		if tag == "dl":
			pass
			#print "Entering folder list; tags are", self.tags

	def handle_endtag(self, tag):
		if tag == "h3":
			self.tags.append(self.currentTag)
			self.currentTag = ""
			self.inH3 = False

		if tag == "a":
			if self.debug == True:
				print
				print "href =", self.href
				print "description =", self.description
				print "tags =", self.tags
				
			# validate href
			validHref = True
			if len(self.href) == 0:
				validHref = False
			if not self.href.split(":")[0] in ["http", "https", "news", "ftp"]:
				validHref = False
			if self.href in self.ignore:
				validHref = False

			# actually post here, make sure there's a url to post
			if validHref:
				bookmark = {
					"href" : self.href,
					"title": self.description,
					"tags" : self.tags
				}
				self.all_items.append(bookmark)
			
			self.href = ""
			self.description = ""
			self.inA = False

		# exiting a dl means end of a bookmarks folder, pop the last tag off
		if tag == "dl":
			self.tags = self.tags[:-1]

	# handle any data: note that this will miss the "escaped" stuff
	# fix this by adding handle_charref, etc methods
	def handle_data(self, data):
		if self.inH3:
			self.currentTag += self.normalizeText(data)

		if self.inA:
			self.description += data

def get_bookmarks(bookmarks_file):
	"""
	Return a list of bookmarks (dictionaries)
	
	each bookmark has the keys:
	href: URL
	title: description
	tags: list of tags/the folder
	"""
	# construct and configure the parser
	if not bookmarks_file:
		return []
	if not os.path.isfile(bookmarks_file):
		return []
	parser = BookmarksParser()

	# initiate the parse; this will submit requests to delicious
	parser.feed(open(bookmarks_file).read())

	# cleanup
	parser.close()
	
	return parser.all_items

def main():
	# go forth
	fileloc = get_firefox_home_file("bookmarks.html")
	print fileloc
	print get_bookmarks(fileloc)

if __name__ == "__main__":
	main()
