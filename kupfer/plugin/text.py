
from kupfer.objects import TextSource, TextLeaf

__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource",)
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

