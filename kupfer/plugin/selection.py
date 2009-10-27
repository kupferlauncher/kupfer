import gtk

from kupfer.objects import Source, Leaf, TextLeaf, SourceLeaf, PicklingHelperMixin
from kupfer import objects
from kupfer.helplib import gobject_connect_weakly

__kupfer_name__ = _("Selected Text")
__kupfer_sources__ = ("SelectionSource", )
__description__ = _("Provides current selection")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SelectedText (TextLeaf):
	qf_id = "selectedtext"
	def __init__(self, text):
		text = objects.tounicode(text)
		lines = filter(None, text.splitlines())
		summary = lines[0] if lines else text
		maxlen = 10
		if len(summary) > maxlen:
			summary = summary[:maxlen] + u".."
		TextLeaf.__init__(self, text, _('Selected Text "%s"') % summary)

	def repr_key(self):
		# return a constant rank key despite the changing name
		return "Selected Text"

class InvisibleSourceLeaf (SourceLeaf):
	"""Hack to hide this source"""
	def is_valid(self):
		return False

class SelectionSource (Source, PicklingHelperMixin):
	def __init__(self):
		Source.__init__(self, _("Selected Text"))
		self.unpickle_finish()

	def unpickle_finish(self):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
		gobject_connect_weakly(clip, "owner-change", self._clipboard_changed)
		self._text = None

	def _clipboard_changed(self, clipboard, event):
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
