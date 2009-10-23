# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os

from kupfer.objects import (Source, UrlLeaf, FilesystemWatchMixin, 
		AppLeafContentMixin)
from kupfer import plugin_support

__kupfer_name__ = _("Opera")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_contents__ = ("BookmarksSource", )
__description__ = _("Index of Opera bookmarks")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)


class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = "opera"

	def __init__(self, name=_("Opera bookmarks")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		self._opera_home = os.path.expanduser("~/.opera/")
		self._bookmarks_path = os.path.join(self._opera_home, 'bookmarks.adr')
		self.monitor_token = self.monitor_directories(self._opera_home)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() == 'bookmarks.adr'

	def get_items(self):
		if not os.path.isfile(self._bookmarks_path):
			return

		name = None
		with open(self._bookmarks_path, 'r') as bfile:
			for line in bfile:
				line = line.strip()
				if line.startswith('NAME='):
					name = line[5:]
				elif line.startswith('URL='):
					if name:
						yield UrlLeaf(line[4:], name)


	def get_description(self):
		return _("")

	def get_icon_name(self):
		return "opera"

	def provides(self):
		yield UrlLeaf

