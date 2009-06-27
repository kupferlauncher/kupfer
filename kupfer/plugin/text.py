from os import path, access, R_OK

from kupfer.objects import TextSource, TextLeaf, FileLeaf

__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", )
__description__ = _("Text queries")
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
