__kupfer_name__ = _("Volumes and Disks")
__kupfer_sources__ = ("VolumesSource", )
__description__ = _("Mounted volumes and disks")
__version__ = "2017.2"
__author__ = ""

from gi.repository import Gio, GLib

from kupfer.objects import Action, Source, FileLeaf
from kupfer.obj.fileactions import Open, OpenTerminal
from kupfer import utils, uiutils


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
        self.kupfer_add_alias(fil.get_basename())

    def get_actions(self):
        yield Open()
        yield OpenTerminal()
        if self.volume.can_eject():
            yield Eject()
        elif self.volume.can_unmount():
            yield Unmount()

    def is_valid(self):
        vm = Gio.VolumeMonitor.get()
        return any(self.volume == v for v in vm.get_mounts())

    def get_description(self):
        return _("Volume mounted at %s") % \
                utils.get_display_path_for_bytestring(self.object)
    def get_gicon(self):
        return self.volume.get_icon()

    @classmethod
    def get_icon_name(self):
        return "drive-removable-media"

class Unmount (Action):
    def __init__(self, name=None):
        super(Unmount, self).__init__(name or _("Unmount"))

    def eject_callback(self, mount, async_result, ctx):
        try:
            mount.eject_with_operation_finish(async_result)
        except GLib.Error:
            ctx.register_late_error()
        else:
            self.success(mount.get_name())

    def unmount_callback(self, mount, async_result, ctx):
        try:
            mount.unmount_with_operation_finish(async_result)
        except GLib.Error:
            ctx.register_late_error()
        else:
            self.success(mount.get_name())

    def success(self, name):
        uiutils.show_notification(_("Unmount finished"),
                                  _('"%s" was successfully unmounted') % name,
                                  icon_name=Volume.get_icon_name())

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        if not leaf.is_valid():
            return
        vol = leaf.volume
        if vol.can_eject():
            vol.eject_with_operation(
                Gio.MountUnmountFlags.NONE,
                None,
                None,
                self.eject_callback,
                ctx)
        elif vol.can_unmount():
            vol.unmount_with_operation(
                Gio.MountUnmountFlags.NONE,
                None,
                None,
                self.unmount_callback, ctx)

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
    source_use_cache = False
    def __init__(self, name=_("Volumes and Disks")):
        super().__init__(name)

    def initialize(self):
        self.vm = Gio.VolumeMonitor.get()
        self.vm.connect("mount-added", self._update)
        self.vm.connect("mount-changed", self._update)
        self.vm.connect("mount-removed", self._update)

    def _update(self, *args):
        self.mark_for_update()
        GLib.timeout_add_seconds(1, lambda: self.mark_for_update())

    def finalize(self):
        del self.vm

    def get_items(self):
        # get_mounts gets all mounted removable media
        return (Volume(v) for v in self.vm.get_mounts())

    def get_description(self):
        return _("Mounted volumes and disks")
    def get_icon_name(self):
        return "drive-removable-media"
    def provides(self):
        yield Volume
