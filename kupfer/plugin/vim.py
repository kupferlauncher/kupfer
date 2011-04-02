__kupfer_name__ = _("Vim")
__kupfer_sources__ = ("RecentsSource", )
__description__ = _("Recently used documents in Vim")
__version__ = "2010-05-01"
__author__ = "Ulrik Sverdrup"

import os

import gio
import glib

from kupfer.objects import Source, FileLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import datatools

def get_vim_files(filepath):
	"""
	Read ~/.viminfo from @filepath

	Look for a line like this:
	*encoding=<encoding>

	Return an iterator of unicode string file paths
	"""
	encoding = "UTF-8"
	recents = []
	with open(filepath, "r") as f:
		for line in f:
			if line.startswith("*encoding="):
				_, enc = line.split("=")
				encoding = enc.strip()
			us_line = line.decode(encoding, "replace")
			## Now find the jumplist
			if us_line.startswith("-'  "):
				parts = us_line.split(None, 3)
				recentfile = os.path.expanduser(parts[-1].strip())
				if recentfile:
					recents.append(recentfile)
	return datatools.UniqueIterator(recents)

class RecentsSource (AppLeafContentMixin, Source):
	appleaf_content_id = ("vim", "gvim")

	vim_viminfo_file = "~/.viminfo"
	def __init__(self, name=None):
		name = name or _("Vim Recent Documents")
		super(RecentsSource, self).__init__(name)

	def initialize(self):
		"""Set up change monitor"""
		viminfofile = os.path.expanduser(self.vim_viminfo_file)
		gfile = gio.File(viminfofile)
		self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._changed)

	def finalize(self):
		if self.monitor:
			self.monitor.cancel()
		self.monitor = None

	def _changed(self, monitor, file1, file2, evt_type):
		"""Change callback; something changed"""
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED,
				gio.FILE_MONITOR_EVENT_CHANGED):
			self.mark_for_update()

	def get_items(self):
		viminfofile = os.path.expanduser(self.vim_viminfo_file)
		if not os.path.exists(viminfofile):
			self.output_debug("Viminfo not found at", viminfofile)
			return

		try:
			filepaths = list(get_vim_files(viminfofile))
		except EnvironmentError:
			self.output_exc()
			return

		for filepath in filepaths:
			# The most confusing glib function
			# takes a unicode string and returns a
			# filesystem-encoded bytestring.
			yield FileLeaf(glib.filename_from_utf8(filepath))

	def get_icon_name(self):
		return "document-open-recent"

	def provides(self):
		yield FileLeaf

