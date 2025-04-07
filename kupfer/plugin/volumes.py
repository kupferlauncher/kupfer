__kupfer_name__ = _("Volumes and Disks")
__kupfer_sources__ = ("VolumesSource",)
__description__ = _("Mounted volumes and disks")
__version__ = "2023-05-01"
__author__ = "US, KB"

import typing as ty

from gi.repository import Gio, GLib

from kupfer import launch
from kupfer.core import commandexec
from kupfer.obj import Action, FileLeaf, Leaf, OpenTerminal, Source
from kupfer.obj.fileactions import Open
from kupfer.ui import uiutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _


_VOLUME_ICON_NAME = "drive-removable-media"


class Volume(FileLeaf):
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
        super().__init__(obj=path, name=volume.get_name())
        self.kupfer_add_alias(fil.get_basename())

    def get_actions(self):
        yield Open()
        yield OpenTerminal()

        if self.volume.can_eject():
            yield Eject()

        if self.volume.can_unmount():
            yield Unmount()

    def is_valid(self):
        vmgr = Gio.VolumeMonitor.get()
        return self.volume in vmgr.get_mounts()

    def get_description(self):
        # TRANS: %s is path where volume is mounted
        return _(
            "Volume mounted at %s"
        ) % launch.get_display_path_for_bytestring(self.object)

    def get_gicon(self):
        return self.volume.get_icon()

    def get_icon_name(self):
        return _VOLUME_ICON_NAME


class VolumeNotMounted(Leaf):
    """The Volume class actually represents one instance of GIO's GMount that
    is not mounted anywhere."""

    # NOTE: marking as non-serializable
    serializable = None

    def __init__(self, volume, device):
        super().__init__(volume, name=volume.get_name())
        self.device = device

    def get_actions(self):
        if self.object.can_mount():
            yield Mount()

    def get_description(self):
        # TRANS: %s is name of device with volume
        return _("Volume on %s") % self.device.get_name()

    def get_gicon(self):
        return self.device.get_icon()

    def get_icon_name(self):
        return _VOLUME_ICON_NAME


class Mount(Action):
    def __init__(self, name=None):
        super().__init__(name or _("Mount"))

    def mount_callback(
        self,
        volume: Gio.Volume,
        async_result: ty.Any,
        ctx: commandexec.ExecutionToken,
    ) -> None:
        try:
            volume.mount_finish(async_result)
        except GLib.Error:
            ctx.register_late_error()
        else:
            uiutils.show_notification(
                _("Mount finished"),
                # TRANS: %s is name of volume
                _('"%s" was successfully mounted') % volume.get_name(),
                icon_name=_VOLUME_ICON_NAME,
            )
            ctx.register_late_result(commandexec.ActionResultRefresh)

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        vol = leaf.object
        if vol.can_mount():
            vol.mount(
                Gio.MountMountFlags.NONE,
                None,
                None,
                self.mount_callback,
                ctx,
            )

    def get_description(self):
        return _("Mount this volume")


class Unmount(Action):
    # prefer eject over umount
    rank_adjust = -5

    def __init__(self, name=None):
        super().__init__(name or _("Unmount"))

    def unmount_callback(
        self,
        mount: Gio.Mount,
        async_result: ty.Any,
        ctx: commandexec.ExecutionToken,
    ) -> None:
        try:
            mount.unmount_with_operation_finish(async_result)
        except GLib.Error:
            # FIXME: argument
            ctx.register_late_error()
        else:
            self.success(mount.get_name())
            ctx.register_late_result(commandexec.ActionResultRefresh)

    def success(self, name: str) -> None:
        uiutils.show_notification(
            _("Unmount finished"),
            # TRANS: %s is name of volume
            _('"%s" was successfully unmounted') % name,
            icon_name=_VOLUME_ICON_NAME,
        )

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        if not leaf.is_valid():
            return

        vol = leaf.volume
        if vol.can_unmount():
            vol.unmount_with_operation(
                Gio.MountUnmountFlags.NONE,
                None,
                None,
                self.unmount_callback,
                ctx,
            )

    def get_description(self):
        return _("Unmount this volume")

    def get_icon_name(self):
        return "media-eject"


class Eject(Unmount):
    def __init__(self):
        super().__init__(_("Eject"))

    def get_description(self):
        return _("Unmount and eject this media")

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        if not leaf.is_valid():
            return

        vol = leaf.volume
        if vol.can_eject():
            vol.eject_with_operation(
                Gio.MountUnmountFlags.NONE,
                None,
                None,
                self.eject_callback,
                ctx,
            )

    def eject_callback(
        self,
        mount: Gio.Mount,
        async_result: ty.Any,
        ctx: commandexec.ExecutionToken,
    ) -> None:
        try:
            mount.eject_with_operation_finish(async_result)
        except GLib.Error:
            ctx.register_late_error()
        else:
            self.success(mount.get_name())
            ctx.register_late_result(commandexec.ActionResultRefresh)


class VolumesSource(Source):
    source_use_cache = False

    def __init__(self, name=_("Volumes and Disks")):
        self.volmon = None
        super().__init__(name)

    def initialize(self):
        self.volmon = Gio.VolumeMonitor.get()
        self.volmon.connect("mount-added", self._update)
        self.volmon.connect("mount-changed", self._update)
        self.volmon.connect("mount-removed", self._update)
        self.volmon.connect("drive-connected", self._update)
        self.volmon.connect("drive-changed", self._update)
        self.volmon.connect("drive-disconnected", self._update)

    def _update(self, *args):
        self.mark_for_update()
        GLib.timeout_add_seconds(1, self.mark_for_update)

    def finalize(self):
        del self.volmon

    def get_items(self):
        assert self.volmon
        # get_mounts gets all mounted removable media
        volumes = self.volmon.get_mounts()
        yield from map(Volume, volumes)

        # add unmounted removable devices
        for dev in self.volmon.get_connected_drives():
            if not dev.is_removable():
                continue

            for vol in dev.get_volumes():
                if vol.can_mount():
                    yield VolumeNotMounted(vol, dev)

    def get_description(self):
        return _("Mounted volumes and disks")

    def get_icon_name(self):
        return "drive-removable-media"

    def provides(self):
        yield Volume
        yield VolumeNotMounted
