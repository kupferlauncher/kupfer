from collections import deque

import gtk

from kupfer.objects import Source, Action, TextLeaf, Leaf, PicklingHelperMixin
from kupfer import utils, plugin_support
from kupfer.helplib import WeakCallback

__kupfer_name__ = _("Clipboards")
__kupfer_sources__ = ("ClipboardSource", )
__kupfer_actions__ = ("CopyToClipboard", )
__description__ = _("Recent clipboards")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "max",
		"label": _("Number of recent clipboards"),
		"type": int,
		"value": 10,
	},
)

class ClipboardText (TextLeaf):
	def get_description(self):
		lines = self.object.splitlines()
		desc = unicode(self)
		numlines = len(lines) or 1

		return ngettext('Clipboard "%(desc)s"',
			'Clipboard with %(num)d lines "%(desc)s"',
			numlines) % {"num": numlines, "desc": desc }

class ClipboardSource (Source, PicklingHelperMixin):
	"""
	"""
	def __init__(self):
		Source.__init__(self, _("Clipboards"))
		self.clipboards = deque()
		self.unpickle_finish()

	def unpickle_finish(self):
		"""Setup change callback on unpickling"""
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		clip.connect("owner-change", WeakCallback(self, "_clipboard_changed"))

	def _clipboard_changed(self, clip, *args):
		max_len = __kupfer_settings__["max"]
		newtext = clip.wait_for_text()
		if not (newtext and newtext.strip()):
			return
		if newtext in self.clipboards:
			self.clipboards.remove(newtext)
		self.clipboards.append(newtext)
		while len(self.clipboards) > max_len:
			self.clipboards.popleft()
		self.mark_for_update()
	
	def get_items(self):
		for t in reversed(self.clipboards):
			yield ClipboardText(t)

	def get_description(self):
		return _("Recent clipboards")

	def get_icon_name(self):
		return "gtk-paste"

	def provides(self):
		yield TextLeaf

class CopyToClipboard (Action):
	def __init__(self):
		Action.__init__(self, _("Copy"))
	def activate(self, leaf):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		clip.set_text(leaf.object)
	def item_types(self):
		yield TextLeaf
	def get_description(self):
		return _("Copy to clipboard")
	def get_icon_name(self):
		return "gtk-copy"
