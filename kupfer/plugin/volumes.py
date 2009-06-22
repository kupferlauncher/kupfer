from kupfer.objects import Leaf, Action, Source
from kupfer import objects, utils

import gio

__kupfer_sources__ = ("VolumesSource", )

class Volume (Leaf):
	def __init__(self, volume):
		self.volume = volume
		fil = self.volume.get_root()
		path = fil.get_path()
		super(Volume, self).__init__(obj=path, name=volume.get_name())

	def get_actions(self):
		yield objects.OpenDirectory()
		yield objects.SearchInside()
		if self.volume.can_eject():
			yield Eject()
		elif self.volume.can_unmount():
			yield Unmount()

	def has_content(self):
		return True
	def content_source(self):
		return objects.DirectorySource(self.object)

	def get_description(self):
		return _("Volume mounted at %s") % self.object
	def get_gicon(self):
		return self.volume.get_icon()
	def get_icon_name(self):
		return "drive-removable-media"

class Eject (Action):
	def __init__(self):
		super(Eject, self).__init__(_("Eject"))

	def _callback(self, *args):
		pass

	def activate(self, leaf):
		vol = leaf.volume
		vol.eject(self._callback)

	def get_description(self):
		return _("Unmount and eject this media")
	def get_icon_name(self):
		return "media-eject"

class Unmount (Action):
	def __init__(self):
		super(Unmount, self).__init__(_("Unmount"))

	def _callback(self, *args):
		pass

	def activate(self, leaf):
		vol = leaf.volume
		vol.unmount(self._callback)

	def get_description(self):
		return _("Unmount this volume")
	def get_icon_name(self):
		return "media-eject"

class VolumesSource (Source):
	def __init__(self, name=_("Volumes and disks")):
		super(VolumesSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_items(self):
		vm = gio.volume_monitor_get()
		# get_mounts gets all mounted removable media
		return (Volume(v) for v in vm.get_mounts())

	def get_description(self):
		return _("Mounted volumes and disks")
	def get_icon_name(self):
		return "drive-removable-media"
