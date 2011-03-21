__kupfer_name__ = _("Volumes and Disks")
__kupfer_sources__ = ("VolumesSource", )
__description__ = _("Mounted volumes and disks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import gio

from kupfer.objects import Leaf, Action, Source, FileLeaf
from kupfer.obj.fileactions import Open, OpenTerminal
from kupfer.objects import OperationError
from kupfer import commandexec
from kupfer import utils


class Volume (FileLeaf):
	"""
	The Volume class actually represents one instance
	of GIO's GMount (as long as it is mounted)
	"""
	# NOTE: marking as non-serializable
	serializable = None

	def __init__(self, volume):
		self.volume = volume
		fil = self.volume.get_root()
		path = fil.get_path()
		super(Volume, self).__init__(obj=path, name=volume.get_name())

	def get_actions(self):
		yield Open()
		yield OpenTerminal()
		if self.volume.can_eject():
			yield Eject()
		elif self.volume.can_unmount():
			yield Unmount()

	def is_valid(self):
		vm = gio.volume_monitor_get()
		return any(self.volume == v for v in vm.get_mounts())

	def get_description(self):
		return _("Volume mounted at %s") % \
				utils.get_display_path_for_bytestring(self.object)
	def get_gicon(self):
		return self.volume.get_icon()
	def get_icon_name(self):
		return "drive-removable-media"

class Unmount (Action):
	def __init__(self, name=None):
		super(Unmount, self).__init__(name or _("Unmount"))

	def eject_callback(self, mount, async_result, token):
		ctx = commandexec.DefaultActionExecutionContext()
		try:
			mount.eject_finish(async_result)
		except gio.Error:
			ctx.register_late_error(token)

	def unmount_callback(self, mount, async_result, token):
		ctx = commandexec.DefaultActionExecutionContext()
		try:
			mount.unmount_finish(async_result)
		except gio.Error:
			ctx.register_late_error(token)

	def activate(self, leaf):
		if not leaf.is_valid():
			return
		ctx = commandexec.DefaultActionExecutionContext()
		token = ctx.get_async_token()
		vol = leaf.volume
		if vol.can_eject():
			vol.eject(self.eject_callback, user_data=token)
		elif vol.can_unmount():
			vol.unmount(self.unmount_callback, user_data=token)

	def get_description(self):
		return _("Unmount this volume")

	def get_icon_name(self):
		return "media-eject"

class Eject (Unmount):
	def __init__(self):
		super(Eject, self).__init__(_("Eject"))

	def get_description(self):
		return _("Unmount and eject this media")

class VolumesSource (Source):
	def __init__(self, name=_("Volumes and Disks")):
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
	def provides(self):
		yield Volume
