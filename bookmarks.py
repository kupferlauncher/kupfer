#!/usr/bin/env python
# -*- coding: utf8 -*-

debug = True

from HTMLParser import HTMLParser

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
			if debug == True:
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
				pass
			
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

def doit(bookmarks_file, base_tag):
	# construct and configure the parser
	parser = BookmarksParser()
	if base_tag and len(base_tag) > 0:
		parser.setBaseTag(base_tag)

	# initiate the parse; this will submit requests to delicious
	parser.feed(open(bookmarks_file).read())

	# cleanup
	parser.close()
	print parser.tags

def usage():
	print "Usage: deli.py --bookmarks=<file> --username=<username> --password=<password [--tag=<tags>]"
	print "	   bookmarks, username, password should be self explanatory"
	print "	   tags is a white-space separated list of tags to apply to all bookmarks"

def main():
	import sys

	# go forth
	doit(sys.argv[1], "test")

main()
