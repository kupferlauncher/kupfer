from os import path

import gio
from gtk import recent_manager_get_default

from kupfer.objects import (Leaf, Action, Source,
		FileLeaf, UrlLeaf, PicklingHelperMixin )
from kupfer import objects

__kupfer_name__ = _("Documents")
__kupfer_sources__ = ("RecentsSource", "PlacesSource", )
__description__ = _("Recently used documents and nautilus places")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class RecentsSource (Source, PicklingHelperMixin):
	def __init__(self):
		super(RecentsSource, self).__init__(_("Recent items"))
		self.max_days = 28
		self.unpickle_finish()

	def unpickle_finish(self):
		"""Set up change callback"""
		manager = recent_manager_get_default()
		manager.connect("changed", self._recent_changed)

	def _recent_changed(self, *args):
		# FIXME: We don't get single item updates, might this be
		# too many updates?
		self.mark_for_update()
	
	def get_items(self):
		count = 0
		manager = recent_manager_get_default()
		items = manager.get_items()
		for item in items:
			day_age = item.get_age()
			if day_age > self.max_days:
				break
			if not item.exists():
				continue

			uri = item.get_uri()
			name = item.get_short_name()
			if item.is_local():
				fileloc = item.get_uri_display()
				yield FileLeaf(fileloc, name)
			else:
				yield UrlLeaf(uri, name)
			count += 1
		self.output_info("Items younger than", self.max_days, "days")

	def get_description(self):
		return _("Recently used documents")
	def get_icon_name(self):
		return "document-open-recent"
	def provides(self):
		yield FileLeaf
		yield UrlLeaf

class PlacesSource (Source):
	"""
	Source for items from nautilus bookmarks 
	"""
	def __init__(self):
		super(PlacesSource, self).__init__(_("Places"))
		self.places_file = "~/.gtk-bookmarks"
	
	def get_items(self):
		"""
		gtk-bookmarks: each line has url and optional title
		file:///path/to/that.end [title]
		"""
		fileloc = path.expanduser(self.places_file)
		if not path.exists(fileloc):
			return ()
		return self._get_places(fileloc)

	def _get_places(self, fileloc):
		for line in open(fileloc):
			if not line.strip():
				continue
			items = line.split()
			uri = items[0]
			gfile = gio.File(uri)
			if len(items) > 1:
				title = items[1]
			else:
				disp = gfile.get_parse_name()
				title =	path.basename(disp)
			locpath = gfile.get_path()
			if locpath:
				yield FileLeaf(locpath, title)
			else:
				yield UrlLeaf(gfile.get_uri(), title)

	def get_description(self):
		return _("Bookmarked locations in Nautilus")
	def get_icon_name(self):
		return "file-manager"
	def provides(self):
		yield FileLeaf
		yield UrlLeaf
