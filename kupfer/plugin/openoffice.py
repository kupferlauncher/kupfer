# -*- coding: UTF-8 -*-

__kupfer_name__ = _("OpenOffice")
__kupfer_sources__ = ("RecentsSource", )
__description__ = _("Recently used documents in OpenOffice")
__version__ = "2009-11-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
from xml.etree import cElementTree as ElementTree
import gio

from kupfer.objects import Source, FileLeaf, UrlLeaf, AppLeaf
from kupfer.obj.helplib import PicklingHelperMixin


_HISTORY_FILE = "~/.openoffice.org/3/user/registry/data/org/openoffice/Office/Histories.xcu"
_NAME_ATTR="{http://openoffice.org/2001/registry}name"

class MultiAppContentMixin (object):
	"""
	Mixin for Source that decorates many app leaves

	This Mixin sees to that the Source is set as content for the applications
	with id 'cls.appleaf_content_id', which may also be a sequence of ids.

	Source has to define the attribute appleaf_content_id and must
	inherit this mixin BEFORE the Source

	This Mixin defines:
	decorates_type,
	decorates_item
	"""
	@classmethod
	def __get_appleaf_id_iter(cls):
		if hasattr(cls.appleaf_content_id, "__iter__"):
			ids = iter(cls.appleaf_content_id)
		else:
			ids = (cls.appleaf_content_id, )
		return ids
	@classmethod
	def decorates_type(cls):
		return AppLeaf
	@classmethod
	def decorate_item(cls, leaf):
		if leaf.get_id() in cls.__get_appleaf_id_iter():
			return cls()


class RecentsSource (MultiAppContentMixin, Source, PicklingHelperMixin):
	appleaf_content_id = [
			"openoffice.org-writer",
			"openoffice.org-base",
			"openoffice.org-calc",
			"openoffice.org-draw",
			"openoffice.org-impress",
			"openoffice.org-math",
			"openoffice.org-startcenter",
	]

	def __init__(self, name=_("OpenOffice Recent Items")):
		Source.__init__(self, name)

	def pickle_prepare(self):
		self.monitor = None

	def initialize(self):
		hist_file_path = _get_history_file_path()
		if not hist_file_path:
			return
		gfile = gio.File(hist_file_path)
		self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
		if self.monitor:
			self.monitor.connect("changed", self._on_history_changed)

	def _on_history_changed(self, monitor, file1, file2, evt_type):
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED,
				gio.FILE_MONITOR_EVENT_CHANGED):
			self.mark_for_update()

	def get_items(self):
		hist_file_path = _get_history_file_path()
		if not hist_file_path:
			return
		
		try:
			tree = ElementTree.parse(hist_file_path)
			node_histories = tree.find('node')
			if (not node_histories \
					or node_histories.attrib[_NAME_ATTR] != 'Histories'):
				return
			
			for list_node in  node_histories.findall('node'):
				if list_node.attrib[_NAME_ATTR] == 'PickList':
					items_node = list_node.find('node')
					if (not items_node \
							or items_node.attrib[_NAME_ATTR] != 'ItemList'):
						return

					for node in items_node.findall('node'):
						hfile = node.attrib[_NAME_ATTR] # file://.....
						if not hfile:
							continue
						gfile = gio.File(hfile)
						if not gfile.query_exists():
							continue
						if gfile.get_path():
							leaf = FileLeaf(gfile.get_path())
						else:
							leaf = UrlLeaf(hfile, gfile.get_basename())
						yield leaf
					break

		except StandardError, err:
			self.output_error(err)

	def get_description(self):
		return _("Recently used documents in OpenOffice")

	def get_icon_name(self):
		return "document-open-recent"

	def provides(self):
		yield FileLeaf
		yield UrlLeaf


def _get_history_file_path():
	path = os.path.expanduser(_HISTORY_FILE)
	return path if os.path.isfile(path) else None

