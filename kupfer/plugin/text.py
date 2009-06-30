from os import path, access, R_OK
from urlparse import urlparse, urlunparse

from kupfer.objects import TextSource, TextLeaf, FileLeaf, UrlLeaf

__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", "URLTextSource",)
__description__ = _("Basic support for free-text queries")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class BasicTextSource (TextSource):
	"""The most basic TextSource yields one TextLeaf"""
	def __init__(self):
		TextSource.__init__(self, name=_("Text matches"))

	def get_items(self, text):
		if not text:
			return
		yield TextLeaf(text)


class PathTextSource (TextSource):
	"""Return existing full paths if typed"""
	def __init__(self):
		TextSource.__init__(self, name=_("Filesystem text matches"))

	def get_rank(self):
		return 80
	def get_items(self, text):
		# Find directories or files
		prefix = path.expanduser("~/")
		filepath = text if path.isabs(text) else path.join(prefix, text)
		if access(filepath, R_OK):
			yield FileLeaf(filepath)

class URLTextSource (TextSource):
	"""detect URLs and webpages"""
	def __init__(self):
		TextSource.__init__(self, name=_("URL text matches"))

	def get_rank(self):
		return 75
	def get_items(self, text):
		""" A bit of hackery to recognize URLs and web addresses
		alike"""
		text = text.strip()
		components = list(urlparse(text))
		domain = "".join(components[1:])
		dotparts = domain.rsplit(".")

		if len(domain.split()) == 1 and (components[0] or ("." in domain and
			len(dotparts) >= 2 and len(dotparts[-1]) >= 2)):
			if not components[0]:
				url = "http://" + "".join(components[1:])
			else:
				url = text
			name = ("".join(components[1:3])).strip("/")
			if name:
				yield UrlLeaf(url, name=name)
