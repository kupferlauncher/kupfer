from __future__ import annotations

__kupfer_name__ = _("Archive Manager")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("UnpackHere", "CreateArchive", "CreateArchiveIn")
__description__ = _("Use Archive Manager actions")
__version__ = "2023-05-15"
__author__ = "Ulrik, KB"

import os
import re
import typing as ty
from pathlib import Path
import shutil

# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer import launch, plugin_support, runtimehelper
from kupfer.core import commandexec
from kupfer.obj import Action, FileLeaf, Leaf, OperationError
from kupfer.obj.special import CommandNotAvailableLeaf
from kupfer.support import fileutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "archive_type",
        "label": _("Compressed archive type for 'Create Archive In'"),
        "type": str,
        "value": ".tar.gz",
        "alternatives": (
            ".7z",
            ".tar",
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
            ".zip",
        ),
    },
    {
        "key": "tool",
        "label": _("Tool used for operations:"),
        "type": str,
        "value": "file-roller",
        "alternatives": (
            "File-roller",
            "7-zip",
            "7za",
        ),
    },
)

_EXTENSIONS_SET = (
    ".7z",
    ".Z",
    ".ace",
    ".alz",
    ".ar",
    ".arj",
    ".bz",
    ".bz2",
    ".cab",
    ".cbr",
    ".cbz",
    ".cpio",
    ".deb",
    ".dmg",
    ".ear",
    ".gz",
    ".iso",
    ".jar",
    ".lha",
    ".lz",
    ".lzh",
    ".lzma",
    ".lzo",
    ".rar",
    ".rpm",
    ".sit",
    ".snap",
    ".sqsh",
    ".tar",
    ".taz",
    ".tbz",
    ".tbz2",
    ".tgz",
    ".tlrz",
    ".tlz",
    ".tzo",
    ".tzst",
    ".war",
    ".xz",
    ".zip",
    ".zoo",
    ".zst",
)


def _tool_cmd_path(tool: str) -> str | None:
    if tool == "7-zip":
        return shutil.which("7z")

    if tool == "7za":
        return shutil.which("7za")

    return shutil.which("file-roller")


class UnpackHere(Action):
    def __init__(self) -> None:
        Action.__init__(self, _("Extract Here"))

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        tool = __kupfer_settings__["tool"]
        if not _tool_cmd_path(tool):
            return CommandNotAvailableLeaf(__name__, __kupfer_name__, tool)

        filedir = str(Path(leaf.object).parent)
        if tool == "7-zip":
            launch.spawn_in_terminal(["7z", "x", leaf.object], filedir)
            return None

        if tool == "7za":
            launch.spawn_in_terminal(["7za", "x", leaf.object], filedir)
            return None

        launch.spawn_async_notify_as(
            "file-roller.desktop",
            ["file-roller", "--extract-here", leaf.object],
        )
        return None

    def valid_for_item(self, leaf):
        fname, ext = os.path.splitext(leaf.object)
        # check for standard extension or a multi-part rar extension
        ext = ext.lower()
        if ext in _EXTENSIONS_SET:
            return True

        # for multi-part archives must exists also file without number, ie:
        # Filename.rar Filename.r00 Filename.r01 etc
        # not sure we can allow decompress no-first archive
        if re.search(r".r\d+$", ext) is not None:
            return os_path.isfile(f"{fname}.rar")

        return False

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Extract compressed archive")

    def get_icon_name(self):
        return "extract-archive"


def _make_archive(filepaths: ty.Iterable[str]) -> None:
    cmd = ["file-roller", "--add"]
    cmd.extend(filepaths)
    launch.spawn_async_notify_as("file-roller.desktop", cmd)


class CreateArchive(Action):
    def __init__(self):
        Action.__init__(self, _("Create Archive"))

    def activate(self, leaf, iobj=None, ctx=None):
        _make_archive((leaf.object,))

    def activate_multiple(self, objs):
        _make_archive(L.object for L in objs)

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Create a compressed archive from folder")

    def get_icon_name(self):
        return "add-files-to-archive"

    def valid_for_item(self, leaf: Leaf) -> bool:
        """Allow to launch this action only with file-roller"""
        tool = __kupfer_settings__["tool"]
        return tool not in ("7-zip", "7za")


def _make_archive_in(
    ctx: commandexec.ExecutionToken,
    basename: str,
    dirpath: str,
    filepaths: ty.Iterable[str],
) -> str:
    archive_type = __kupfer_settings__["archive_type"]
    archive_path = fileutils.get_destpath_in_directory(
        dirpath, basename, archive_type
    )

    tool = __kupfer_settings__["tool"]
    if not _tool_cmd_path(tool):
        raise OperationError(f"Command {tool} not available")

    if tool in ("7-zip", "7za"):
        cmd = ["7za" if tool == "7za" else "7z", "a", archive_path]
        cmd.extend(filepaths)
        launch.spawn_in_terminal(cmd)

    else:
        cmd = ["file-roller", f"--add-to={archive_path}"]
        cmd.extend(filepaths)
        launch.spawn_async_notify_as("file-roller.desktop", cmd)

    runtimehelper.register_async_file_result(ctx, archive_path)
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
        _make_archive_in(ctx, basename, dirpath, (leaf.object,))

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
        return fileutils.is_directory_writable(obj.object)

    def get_description(self):
        return _("Create a compressed archive from folder")

    def get_icon_name(self):
        return "add-files-to-archive"
