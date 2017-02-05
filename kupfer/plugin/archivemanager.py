__kupfer_name__ = _("Archive Manager")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
        "UnpackHere",
        "CreateArchive",
        "CreateArchiveIn",
    )
__description__ = _("Use Archive Manager actions")
__version__ = ""
__author__ = "Ulrik"

import os
import re
# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer.objects import Action, FileLeaf
from kupfer import utils 
from kupfer import plugin_support
from kupfer import runtimehelper


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "archive_type",
        "label": _("Compressed archive type for 'Create Archive In'"),
        "type": str,
        "value": ".tar.gz",
        "alternatives": (
            ".7z",
            ".rar",
            ".tar",
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
            ".zip",
            )
    },
)

class UnpackHere (Action):
    def __init__(self):
        Action.__init__(self, _("Extract Here"))
        self.extensions_set = set((
            ".rar", ".7z", ".zip", ".gz", ".tgz", ".tar", ".lzma", ".bz2",
            ".tbz2", ".tzo", ".lzo", ".xz", ".ar", ".cbz", ".Z", ".taz",
            ".lz", ".bz", ".tbz", ".lzh",
            ))
    def activate(self, leaf):
        utils.spawn_async_notify_as("file-roller.desktop",
                ["file-roller", "--extract-here", leaf.object])

    def valid_for_item(self, item):
        tail, ext = os.path.splitext(item.object)
        # FIXME: Make this detection smarter
        # check for standard extension or a multi-part rar extension
        return (ext.lower() in self.extensions_set or
            re.search(r".r\d+$", ext.lower()) is not None)

    def item_types(self):
        yield FileLeaf
    def get_description(self):
        return _("Extract compressed archive")
    def get_icon_name(self):
        return "extract-archive"

class CreateArchive (Action):
    def __init__(self):
        Action.__init__(self, _("Create Archive"))

    @classmethod
    def _make_archive(cls, filepaths):
        cmd = ["file-roller", "--add"]
        cmd.extend(filepaths)
        utils.spawn_async_notify_as("file-roller.desktop", cmd)

    def activate(self, leaf):
        self._make_archive((leaf.object, ))
    def activate_multiple(self, objs):
        self._make_archive([L.object for L in objs])

    def item_types(self):
        yield FileLeaf
    def get_description(self):
        return _("Create a compressed archive from folder")
    def get_icon_name(self):
        return "add-files-to-archive"

class CreateArchiveIn (Action):
    def __init__(self):
        Action.__init__(self, _("Create Archive In..."))

    @classmethod
    def _make_archive(cls, ctx, basename, dirpath, filepaths):
        archive_type = __kupfer_settings__["archive_type"]
        archive_path = \
            utils.get_destpath_in_directory(dirpath, basename, archive_type)
        cmd = ["file-roller", "--add-to=%s" % (archive_path, )]
        cmd.extend(filepaths)
        runtimehelper.register_async_file_result(ctx, archive_path)
        utils.spawn_async_notify_as("file-roller.desktop", cmd)
        return archive_path

    def wants_context(self):
        return True

    def activate(self, leaf, iobj, ctx):
        dirpath = iobj.object
        basename = os_path.basename(leaf.object)
        self._make_archive(ctx, basename, dirpath, (leaf.object, ))

    def activate_multiple(self, objs, iobjs, ctx):
        # TRANS: Default filename (no extension) for 'Create Archive In...'
        basename = _("Archive")
        for iobj in iobjs:
            self._make_archive(ctx, basename, iobj.object,
                               [L.object for L in objs])

    def item_types(self):
        yield FileLeaf
    def requires_object(self):
        return True
    def object_types(self):
        yield FileLeaf
    def valid_object(self, obj, for_item=None):
        return utils.is_directory_writable(obj.object)
    def get_description(self):
        return _("Create a compressed archive from folder")
    def get_icon_name(self):
        return "add-files-to-archive"

