__kupfer_name__ = _("Documents")
__description__ = _("Recently used documents and bookmarked folders")
__kupfer_sources__ = ("RecentsSource", "PlacesSource", )
__kupfer_contents__ = ("ApplicationRecentsSource", )
__kupfer_category__ = ("files", )
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from os import path

import gio
from gtk import recent_manager_get_default

from kupfer.objects import (Leaf, Action, Source,
		AppLeaf, FileLeaf, UrlLeaf, )
from kupfer import objects, plugin_support
from kupfer import launch, icons
from kupfer.weaklib import gobject_connect_weakly

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "max_days",
		"label": _("Max recent document days"),
		"type": int,
		"value": 28,
	},
)


class RecentsSource (Source):
	def __init__(self, name=None):
		if not name:
			name = _("Recent Items")
		super(RecentsSource, self).__init__(name)

	def initialize(self):
		"""Set up change callback"""
		manager = recent_manager_get_default()
		gobject_connect_weakly(manager, "changed", self._recent_changed)

	def _recent_changed(self, *args):
		# FIXME: We don't get single item updates, might this be
		# too many updates?
		self.mark_for_update()
	
	def get_items(self):
		max_days = __kupfer_settings__["max_days"]
		self.output_info("Items younger than", max_days, "days")
		items = self._get_items(max_days)
		return items

	@classmethod
	def _get_items(cls, max_days, for_application_named=None):
		manager = recent_manager_get_default()
		items = manager.get_items()
		item_leaves = []
		for item in items:
			if for_application_named:
				low_apps = [A.lower() for A in item.get_applications()]
				if for_application_named.lower() not in low_apps:
					continue
			day_age = item.get_age()
			if max_days >= 0 and day_age > max_days:
				continue
			if not item.exists():
				continue

			uri = item.get_uri()
			name = item.get_short_name()
			if item.is_local():
				leaf = FileLeaf(gio.File(uri).get_path())
			else:
				leaf = UrlLeaf(uri, name)
			item_leaves.append((leaf, item.get_modified()))
		for lf, date in sorted(item_leaves, key=lambda t: t[1], reverse=True):
			yield lf

	def get_description(self):
		return _("Recently used documents")

	def get_icon_name(self):
		return "document-open-recent"
	def provides(self):
		yield FileLeaf
		yield UrlLeaf

class ApplicationRecentsSource (RecentsSource):
	def __init__(self, application):
		name = _("%s Documents") % unicode(application)
		super(ApplicationRecentsSource, self).__init__(name)
		self.application = application

	def repr_key(self):
		return self.application.repr_key()

	def get_items(self):
		svc = launch.GetApplicationsMatcherService()
		app_name = svc.application_name(self.application.get_id())
		max_days = -1
		self.output_info("Items for", app_name)
		items = self._get_items(max_days, app_name)
		return items

	@classmethod
	def has_items_for_application(cls, name):
		for item in cls._get_items(-1, name):
			return True
		return False

	def get_gicon(self):
		return icons.ComposedIcon(self.get_icon_name(),
				self.application.get_icon())
	def get_description(self):
		return _("Recently used documents for %s") % unicode(self.application)

	@classmethod
	def decorates_type(cls):
		return AppLeaf

	@classmethod
	def decorate_item(cls, leaf):
		svc = launch.GetApplicationsMatcherService()
		app_name = svc.application_name(leaf.get_id())
		if app_name and cls.has_items_for_application(app_name):
			return cls(leaf)
		return None

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
		return _("Bookmarked folders")
	def get_icon_name(self):
		return "file-manager"
	def provides(self):
		yield FileLeaf
		yield UrlLeaf
