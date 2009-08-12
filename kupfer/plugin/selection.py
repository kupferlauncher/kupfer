import gtk

from kupfer.objects import Source, Leaf, TextLeaf, SourceLeaf, PicklingHelperMixin

__kupfer_name__ = _("Selected Text")
__kupfer_sources__ = ("SelectionSource", )
__description__ = _("Provides current selection")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SelectedText (TextLeaf):
	def __init__(self, text):
		TextLeaf.__init__(self, text, _("Selected Text"))

class InvisibleSourceLeaf (SourceLeaf):
	"""Hack to hide this source"""
	def is_valid(self):
		return False

class SelectionSource (Source, PicklingHelperMixin):
	def __init__(self):
		Source.__init__(self, _("Selected Text"))
		self.unpickle_finish()

	def unpickle_finish(self):
		clipboard = gtk.clipboard_get("PRIMARY")
		clipboard.connect("owner-change", self._clipboard_owner_changed)
		self._text = None

	def _clipboard_owner_changed(self, clipboard, event):
		self._text = clipboard.wait_for_text()
		self.mark_for_update()

	def get_items(self):
		if self._text:
			yield SelectedText(self._text)

	def get_description(self):
		return _("Provides current selection")
	def provides(self):
		yield TextLeaf
	def get_leaf_repr(self):
		return InvisibleSourceLeaf(self)
