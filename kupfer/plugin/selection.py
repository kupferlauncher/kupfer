import gtk

from kupfer.objects import Source, Leaf, TextLeaf

__kupfer_name__ = _("Selected Text")
__kupfer_sources__ = ("SelectionSource", )
__description__ = _("Provides currently Selected text")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SelectedText (TextLeaf):
	def __init__(self, text):
		TextLeaf.__init__(self, text, _("Selected Text"))

class SelectionSource (Source):
	def __init__(self):
		Source.__init__(self, _("Selected Text source"))

	def is_dynamic(self):
		return True
	def get_items(self):
		clipboard = gtk.clipboard_get("PRIMARY")
		text = clipboard.wait_for_text()
		if text:
			yield SelectedText(text)

	def get_description(self):
		return _("Provides currently Selected text")
	def provides(self):
		yield TextLeaf
