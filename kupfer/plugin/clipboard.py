from collections import deque

import gtk

from kupfer.objects import Source, Action, TextLeaf, Leaf
from kupfer import utils

__kupfer_name__ = _("Clipboard")
__kupfer_sources__ = ("ClipboardSource", )
__kupfer_actions__ = ("CopyToClipboard", )
__description__ = _("Recent clipboards")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class ClipboardText (TextLeaf):
	def __init__(self, text):
		# take first non-empty line
		firstline = [l for l in text.splitlines() if l.strip()][0]
		Leaf.__init__(self, text, firstline)
	def get_description(self):
		lines = self.object.splitlines()
		desc = unicode(self)
		numlines = ""
		if len(lines) > 1:
			numlines = _("%d lines") % len(lines)

		return _('Clipboard with %s "%s"') % (numlines, desc)

class ClipboardSource (Source):
	"""
	"""
	def __init__(self):
		Source.__init__(self, _("Clipboards"))
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		clip.connect("owner-change", self._clipboard_changed)
		self.clipboards = deque()
		self.max_len = 10

	def _clipboard_changed(self, clip, *args):
		newtext = clip.wait_for_text()
		if not (newtext and newtext.strip()):
			return
		if newtext in self.clipboards:
			self.clipboards.remove(newtext)
		self.clipboards.append(newtext)
		while len(self.clipboards) > self.max_len:
			self.clipboards.popleft()
		self.mark_for_update()
	
	def __setstate__(self, state):
		"""Setup change callback on unpickling"""
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		clip.connect("owner-change", self._clipboard_changed)
		self.__dict__.update(state)

	def __getstate__(self):
		return self.__dict__

	def get_items(self):
		for t in reversed(self.clipboards):
			yield ClipboardText(t)

	def get_description(self):
		return _("Recent clipboards")

	def get_icon_name(self):
		return "copy"
	def provides(self):
		yield TextLeaf

class CopyToClipboard (Action):
	def __init__(self):
		Action.__init__(self, _("Copy"))
	def activate(self, leaf):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		clip.set_text(leaf.object)
	def item_types(self):
		yield ClipboardText
	def get_description(self):
		return _("Copy to clipboard")
	def get_icon_name(self):
		return "gtk-copy"
