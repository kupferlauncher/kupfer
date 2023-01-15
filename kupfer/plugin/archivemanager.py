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
import typing as ty

# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer import plugin_support, runtimehelper, utils
from kupfer.obj import Action, FileLeaf

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "archive_type",
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
        ),
    },
)

_EXTENSIONS_SET = {
    ".rar",
    ".7z",
    ".zip",
    ".gz",
    ".tgz",
    ".tar",
    ".lzma",
    ".bz2",
    ".tbz2",
    ".tzo",
    ".lzo",
    ".xz",
    ".ar",
    ".cbz",
    ".Z",
    ".taz",
    ".lz",
    ".bz",
    ".tbz",
    ".lzh",
}


class UnpackHere(Action):
    def __init__(self):
        Action.__init__(self, _("Extract Here"))

    def activate(self, leaf, iobj=None, ctx=None):
        utils.spawn_async_notify_as(
            "file-roller.desktop",
            ["file-roller", "--extract-here", leaf.object],
        )

    def valid_for_item(self, leaf):
        _tail, ext = os.path.splitext(leaf.object)
        # FIXME: Make this detection smarter
        # check for standard extension or a multi-part rar extension
        ext = ext.lower()
        return ext in _EXTENSIONS_SET or re.search(r".r\d+$", ext) is not None

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Extract compressed archive")

    def get_icon_name(self):
        return "extract-archive"


def _make_archive(filepaths: ty.Iterable[str]) -> None:
    cmd = ["file-roller", "--add"]
    cmd.extend(filepaths)
    utils.spawn_async_notify_as("file-roller.desktop", cmd)


class CreateArchive(Action):
    def __init__(self):
        Action.__init__(self, _("Create Archive"))

    def activate(self, leaf):
        _make_archive((leaf.object,))

    def activate_multiple(self, objs):
        _make_archive((L.object for L in objs))

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Create a compressed archive from folder")

    def get_icon_name(self):
        return "add-files-to-archive"


def _make_archive_in(
    ctx, basename: str, dirpath: str, filepaths: ty.Iterable[str]
) -> str:
    archive_type = __kupfer_settings__["archive_type"]
    archive_path = utils.get_destpath_in_directory(
        dirpath, basename, archive_type
    )
    cmd = ["file-roller", f"--add-to={archive_path}"]
    cmd.extend(filepaths)
    runtimehelper.register_async_file_result(ctx, archive_path)
    utils.spawn_async_notify_as("file-roller.desktop", cmd)
    return archive_path


class CreateArchiveIn(Action):
    def __init__(self):
        Action.__init__(self, _("Create Archive In..."))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        assert ctx
        dirpath = iobj.object
        basename = os_path.basename(leaf.object)
        self._make_archive(ctx, basename, dirpath, (leaf.object,))

    def activate_multiple(self, objs, iobjs, ctx):
        # TRANS: Default filename (no extension) for 'Create Archive In...'
        basename = _("Archive")
        for iobj in iobjs:
            _make_archive_in(
                ctx, basename, iobj.object, (L.object for L in objs)
            )

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
