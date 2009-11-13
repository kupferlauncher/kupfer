# -*- coding: UTF-8 -*-

import os
from xml.etree import ElementTree
import gio

from kupfer.objects import (Action, Source, Leaf, PicklingHelperMixin, 
		AppLeafContentMixin)
from kupfer import utils

__kupfer_name__ = _("TrueCrypt")
__kupfer_sources__ = ("VolumeSource", )
__description__ = _("Volumes from TrueCrypt History.")
__version__ = "1.0"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


_HISTORY_FILE = "~/.TrueCrypt/History.xml"


class Volume(Leaf):
	def __init__(self, path, name):
		Leaf.__init__(self, path, name)

	def get_icon_name(self):
		return "truecrypt"

	def get_description(self):
		return _("TrueCrypt Volume: %(file)s") % dict(file=self.object)

	def get_actions(self):
		yield MountVolume()


class MountVolume(Action):
	def __init__(self):
		Action.__init__(self, _("Mount Volume"))
		
	def activate(self, leaf):
		utils.launch_commandline('truecrypt ' + leaf.object)


class VolumeSource (AppLeafContentMixin, Source, PicklingHelperMixin):
	appleaf_content_id = "truecrypt"

	def __init__(self, name=_("TrueCrypt Volumes")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def pickle_prepare(self):
		self.monitor = None

	def unpickle_finish(self):
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
			for volume in tree.find('history').findall('volume'):
				volume_path = volume.text
				if volume_path:
					gfile = gio.File(volume_path)
					if not gfile.query_exists():
						continue
					
					yield Volume(gfile.get_path(), gfile.get_basename())

		except StandardError, err:
			self.output_error(err)

	def get_description(self):
		return _("Volumes from TrueCrypt History")

	def get_icon_name(self):
		return "truecrypt"

	def provides(self):
		yield Volume


def _get_history_file_path():
	path = os.path.expanduser(_HISTORY_FILE)
	return path if os.path.isfile(path) else None

