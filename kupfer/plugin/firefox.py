# encoding: utf-8
from __future__ import with_statement

__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__description__ = _("Index of Firefox bookmarks")
__version__ = "2010-01-23"
__author__ = "Ulrik, William Friesen, Karol Będkowski"

from contextlib import closing
import os
import itertools
import sqlite3

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer import plugin_support
from kupfer.plugin import firefox_support


__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)

class BookmarksSource (AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = ("firefox", "iceweasel")
	def __init__(self):
		super(BookmarksSource, self).__init__(_("Firefox Bookmarks"))
		self._history = []
		self._version = 2

	def initialize(self):
		ff_home = firefox_support.get_firefox_home_file('')
		self.monitor_token = self.monitor_directories(ff_home)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() == 'lock'

	def _get_ffx3_history(self):
		"""Query the firefox places database"""
		max_history_items = 25
		fpath = firefox_support.get_firefox_home_file("places.sqlite")
		if not (fpath and os.path.isfile(fpath)):
			return
		try:
			self.output_debug("Reading history from", fpath)
			with closing(sqlite3.connect(fpath, timeout=1)) as conn:
				c = conn.cursor()
				c.execute("""SELECT DISTINCT(url), title
				             FROM moz_places
				             ORDER BY visit_count DESC
				             LIMIT ?""",
				             (max_history_items,))
				return [UrlLeaf(url, title) for url, title in c]
		except sqlite3.Error, exc:
			# Something is wrong with the database
			self.output_error(exc)

	def _get_ffx3_bookmarks(self, fpath):
		"""Parse Firefox' .json bookmarks backups"""
		from kupfer.plugin import firefox3_support
		self.output_debug("Parsing", fpath)
		bookmarks = firefox3_support.get_bookmarks(fpath)
		for book in bookmarks:
			yield UrlLeaf(book["uri"], book["title"])

	def _get_ffx2_bookmarks(self, fpath):
		"""Parse Firefox' bookmarks.html"""
		self.output_debug("Parsing", fpath)
		bookmarks = firefox_support.get_bookmarks(fpath)
		for book in bookmarks:
			yield UrlLeaf(book["href"], book["title"])

	def get_items(self):
		# try to update the history file
		history_items = self._get_ffx3_history()
		if history_items is not None:
			self._history = history_items

		# now try reading JSON bookmark backups,
		# with html bookmarks as backup
		dirloc = firefox_support.get_firefox_home_file("bookmarkbackups")
		fpath = None
		if dirloc:
			files = os.listdir(dirloc)
			if files:
				latest_file = (files.sort() or files)[-1]
				fpath = os.path.join(dirloc, latest_file)

		if fpath and os.path.splitext(fpath)[-1].lower() == ".json":
			try:
				json_bookmarks = list(self._get_ffx3_bookmarks(fpath))
			except Exception, exc:
				# Catch JSON parse errors
				# different exception for cjson and json
				self.output_error(exc)
			else:
				return itertools.chain(self._history, json_bookmarks)

		fpath = firefox_support.get_firefox_home_file("bookmarks.html")
		if fpath:
			html_bookmarks = self._get_ffx2_bookmarks(fpath)
		else:
			self.output_error("No firefox bookmarks file found")
			html_bookmarks = []
		return itertools.chain(self._history, html_bookmarks)

	def get_description(self):
		return _("Index of Firefox bookmarks")
	def get_gicon(self):
		return self.get_leaf_repr() and self.get_leaf_repr().get_gicon()
	def get_icon_name(self):
		return "web-browser"
	def provides(self):
		yield UrlLeaf
