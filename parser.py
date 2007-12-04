#!/usr/bin/python

"""
Parse a bookmarks html file
and return a list of links
"""

from xml.sax import make_parser
from xml.sax.handler import ContentHandler


class BookmarksParser(ContentHandler):

	def __init__ (self):
		self.in_link_element = False
		self.link_content = None
		self.link_list = []
	
	def startElement(self, name, attrs):
		if name == "a":
			if self.in_link_element:
				raise
			self.in_link_element = True
			self.link_content = ""
			self.link_href = attrs.get("href", "")
			for k, v in zip(attrs.keys(), attrs.items()):
				print k,v 


	def characters (self, chars):
		if self.in_link_element:
			self.link_content += chars

	def endElement(self, name):
		if name == "a":
			self.link_list.append((self.link_content, self.link_href))
			self.in_link_element = False

import sys
file_in = sys.argv[1]

parser = make_parser()   
handler = BookmarksParser()
parser.setContentHandler(handler)
parser.parse(open(file_in))

print handler.link_list
