# -*- coding: UTF-8 -*-
from __future__ import with_statement

import codecs
import os

from kupfer.objects import (Source, UrlLeaf, FilesystemWatchMixin,
		AppLeafContentMixin)
from kupfer import plugin_support, objects


__kupfer_name__ = _("Opera Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_contents__ = ("BookmarksSource", )
__description__ = _("Index of Opera bookmarks")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)

BOOKMARKS_FILE = "bookmarks.adr"

class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = "opera"

	def __init__(self, name=_("Opera Bookmarks")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		self._opera_home = os.path.expanduser("~/.opera/")
		self._bookmarks_path = os.path.join(self._opera_home, BOOKMARKS_FILE)
		self.monitor_token = self.monitor_directories(self._opera_home)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() == BOOKMARKS_FILE

	def get_items(self):
		name = None
		try:
			with codecs.open(self._bookmarks_path, "r", "UTF-8") as bfile:
				for line in bfile:
					line = line.strip()
					if line.startswith(u'NAME='):
						name = line[5:]
					elif line.startswith(u'URL=') and name:
						yield UrlLeaf(line[4:], name)
		except EnvironmentError, exc:
			self.output_error(exc)
		except UnicodeError, exc:
			self.output_error("File %s not in expected encoding (UTF-8)" %
					self._bookmarks_path)
			self.output_error(exc)

	def get_description(self):
		return _("Index of Opera bookmarks")

	def get_icon_name(self):
		return "opera"

	def provides(self):
		yield UrlLeaf

