__kupfer_name__ = _("Clipboards")
__kupfer_sources__ = ("ClipboardSource", )
__kupfer_actions__ = ("ClearClipboards", )
__description__ = _("Recent clipboards and clipboard proxy objects")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from collections import deque

import gio
import gtk

from kupfer.objects import Source, TextLeaf, Action, SourceLeaf
from kupfer.objects import FileLeaf
from kupfer.obj.compose import MultipleLeaf
from kupfer import plugin_support
from kupfer.weaklib import gobject_connect_weakly


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "max",
		"label": _("Number of recent clipboards to remember"),
		"type": int,
		"value": 10,
	},
	{
		"key" : "use_selection",
		"label": _("Include selected text in clipboard history"),
		"type": bool,
		"value": False,
	},
	{
		"key" : "sync_selection",
		"label": _("Copy selected text to primary clipboard"),
		"type": bool,
		"value": False,
	},
)

URI_TARGET="text/uri-list"

class ClipboardText (TextLeaf):
	def get_description(self):
		numlines = max(self.object.count("\n"), 1)
		desc = self.get_first_text_line(self.object)

		return ngettext('Clipboard "%(desc)s"',
			'Clipboard with %(num)d lines "%(desc)s"',
			numlines) % {"num": numlines, "desc": desc }

class CurrentClipboardText (ClipboardText):
	qf_id = "clipboardtext"
	def __init__(self, text):
		ClipboardText.__init__(self, text, _('Clipboard Text'))

class CurrentClipboardFile (FileLeaf):
	"represents the *unique* current clipboard file"
	qf_id = "clipboardfile"
	def __init__(self, filepath):
		"""@filepath is a filesystem byte string `str`"""
		FileLeaf.__init__(self, filepath, _('Clipboard File'))

	def __repr__(self):
		return "<%s %s>" % (__name__, self.qf_id)

class CurrentClipboardFiles (MultipleLeaf):
	"represents the *unique* current clipboard if there are many files"
	qf_id = "clipboardfile"
	def __init__(self, paths):
		files = [FileLeaf(path) for path in paths]
		MultipleLeaf.__init__(self, files, _("Clipboard Files"))

	def __repr__(self):
		return "<%s %s>" % (__name__, self.qf_id)


class ClearClipboards(Action):
	def __init__(self):
		Action.__init__(self, _("Clear"))

	def activate(self, leaf):
		leaf.object.clear()

	def item_types(self):
		yield SourceLeaf

	def valid_for_item(self, leaf):
		return isinstance(leaf.object, ClipboardSource)

	def get_description(self):
		return _("Remove all recent clipboards")

	def get_icon_name(self):
		return "edit-clear"


class ClipboardSource (Source):
	def __init__(self):
		Source.__init__(self, _("Clipboards"))
		self.clipboards = deque()

	def initialize(self):
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
		gobject_connect_weakly(clip, "owner-change", self._clipboard_changed)
		clip = gtk.clipboard_get(gtk.gdk.SELECTION_PRIMARY)
		gobject_connect_weakly(clip, "owner-change", self._clipboard_changed)
		self.clipboard_uris = []
		self.clipboard_text = None

	def finalize(self):
		self.clipboard_uris = []
		self.clipboard_text = None
		self.mark_for_update()

	def _clipboard_changed(self, clip, event, *args):
		is_selection = (event.selection == gtk.gdk.SELECTION_PRIMARY)
		if is_selection and not __kupfer_settings__["use_selection"]:
			return

		max_len = __kupfer_settings__["max"]
		newtext = clip.wait_for_text()
		self.clipboard_text = newtext
		if clip.wait_is_target_available(URI_TARGET):
			sdata = clip.wait_for_contents(URI_TARGET)
			self.clipboard_uris = list(sdata.get_uris())
		else:
			self.clipboard_uris = []
		if not (newtext and newtext.strip()):
			return

		if newtext in self.clipboards:
			self.clipboards.remove(newtext)
		# if the previous text is a prefix of the new selection, supercede it
		if (is_selection and self.clipboards
				and (newtext.startswith(self.clipboards[-1])
				or newtext.endswith(self.clipboards[-1]))):
			self.clipboards.pop()
		self.clipboards.append(newtext)

		if is_selection and __kupfer_settings__["sync_selection"]:
			gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD).set_text(newtext)

		while len(self.clipboards) > max_len:
			self.clipboards.popleft()
		self.mark_for_update()

	def get_items(self):
		# produce the current clipboard files if any
		paths = filter(None, 
		        [gio.File(uri=uri).get_path() for uri in self.clipboard_uris])
		if len(paths) == 1:
			yield CurrentClipboardFile(paths[0])
		if len(paths) > 1:
			yield CurrentClipboardFiles(paths)

		# put out the current clipboard text
		if self.clipboard_text:
			yield CurrentClipboardText(self.clipboard_text)
		# put out the clipboard history
		for t in reversed(self.clipboards):
			yield ClipboardText(t)

	def get_description(self):
		return __description__

	def get_icon_name(self):
		return "edit-paste"

	def provides(self):
		yield TextLeaf
		yield FileLeaf
		yield MultipleLeaf

	def clear(self):
		self.clipboards.clear()
		self.mark_for_update()
