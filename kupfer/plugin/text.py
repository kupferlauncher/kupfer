from os import path, access, R_OK
from urlparse import urlparse, urlunparse

import gobject

from kupfer.objects import TextSource, TextLeaf, FileLeaf, UrlLeaf

__kupfer_name__ = _("Free-text Queries")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", "URLTextSource",)
__description__ = _("Basic support for free-text queries")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class BasicTextSource (TextSource):
	"""The most basic TextSource yields one TextLeaf"""
	def __init__(self):
		TextSource.__init__(self, name=_("Text Matches"))

	def get_items(self, text):
		if not text:
			return
		yield TextLeaf(text)
	def provides(self):
		yield TextLeaf


class PathTextSource (TextSource):
	"""Return existing full paths if typed"""
	def __init__(self):
		TextSource.__init__(self, name=_("Filesystem Text Matches"))

	def get_rank(self):
		return 80
	def get_items(self, text):
		# Find directories or files
		prefix = path.expanduser(u"~/")
		filepath = text if path.isabs(text) else path.join(prefix, text)
		# use filesystem encoding here
		filepath = gobject.filename_from_utf8(filepath)
		if access(filepath, R_OK):
			yield FileLeaf(filepath)
	def provides(self):
		yield FileLeaf

class URLTextSource (TextSource):
	"""detect URLs and webpages"""
	def __init__(self):
		TextSource.__init__(self, name=_("URL Text Matches"))

	def get_rank(self):
		return 75
	def get_items(self, text):
		text = text.strip()
		components = list(urlparse(text))
		domain = "".join(components[1:])
		dotparts = domain.rsplit(".")

		# 1. Domain name part is one word (without spaces)
		# 2. Urlparse parses a scheme (http://), else we apply heuristics
		if len(domain.split()) == 1 and (components[0] or ("." in domain and
			len(dotparts) >= 2 and len(dotparts[-1]) >= 2 and
			any(char.isalpha() for char in domain) and
			all(part[:1].isalnum() for part in dotparts))):
			if not components[0]:
				url = "http://" + "".join(components[1:])
			else:
				url = text
			name = ("".join(components[1:3])).strip("/")
			if name:
				yield UrlLeaf(url, name=name)
	def provides(self):
		yield UrlLeaf
