# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os
import gio
from xml.etree import cElementTree as ElementTree

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin, UrlLeaf
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import utils

__kupfer_name__ = _("Vinagre")
__kupfer_sources__ = ("SessionSource", )
__kupfer_actions__ = ('VinagreStartSession', )
__description__ = _("Vinagre bookmarks and actions")
__version__ = "2009-11-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


BOOKMARKS_FILE = '~/.local/share/vinagre/vinagre-bookmarks.xml'

class Bookmark(Leaf):
	def __init__(self, url, name):
		Leaf.__init__(self, url, name)
		self._description = url 

	def get_actions(self):
		yield VinagreStartSession()

	def get_description(self):
		return self._description

	def get_icon_name(self):
		return "computer"


class VinagreStartSession(Action):
	def __init__(self):
		Action.__init__(self, _('Start Vinagre Session'))

	def activate(self, leaf):
		utils.launch_commandline("vinagre %s" % leaf.object)

	def get_icon_name(self):
		return 'vinagre'

	def item_types(self):
		yield Bookmark
		yield UrlLeaf

	def valid_for_item(self, item):
		return (item.object.startswith('ssh://') \
				or item.object.startswith('vnc://'))


class SessionSource(AppLeafContentMixin, Source, PicklingHelperMixin,
		FilesystemWatchMixin):
	appleaf_content_id = 'vinagre'

	def __init__(self, name=_("Vinagre Bookmarks")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def pickle_prepare(self):
		self.monitor = None

	def unpickle_finish(self):
		self._bookmark_file = os.path.expanduser(BOOKMARKS_FILE)
		gfile = gio.File(self._bookmark_file)
		self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._on_bookmarks_changed)

	def _on_bookmarks_changed(self, monitor, file1, file2, evt_type):
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED,
				gio.FILE_MONITOR_EVENT_CHANGED):
			self.mark_for_update()

	def get_items(self):
		if not os.path.isfile(self._bookmark_file):
			return

		try:
			tree = ElementTree.parse(self._bookmark_file)
			for item in tree.findall('item'):
				protocol = item.find('protocol').text
				name = item.find('name').text
				host = item.find('host').text
				port = item.find('port').text
				url = '%s://%s:%s' % (protocol, host, port)
				yield Bookmark(url, name)
		except StandardError, err:
			self.output_error(err)

	def get_description(self):
		return None

	def get_icon_name(self):
		return "vinagre"

	def provides(self):
		yield Bookmark


