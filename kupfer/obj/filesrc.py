"""
File - related sources

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

from __future__ import annotations

import os
import typing as ty
from contextlib import suppress
from os import path

from gi.repository import GdkPixbuf, Gio, GLib

from kupfer import icons
from kupfer.support import fileutils
from kupfer.obj import apps, files
from kupfer.obj.base import Leaf, Source
from kupfer.obj.exceptions import InvalidDataError
from kupfer.obj.helplib import FilesystemWatchMixin

__all__ = (
    "construct_file_leaf",
    "DirectorySource",
    "FileSource",
)

if ty.TYPE_CHECKING:
    _ = str


def construct_file_leaf(obj: str) -> Leaf:
    """If the path in @obj points to a Desktop Item file,
    return an AppLeaf, otherwise return a FileLeaf
    """
    if obj.endswith(".desktop"):
        with suppress(InvalidDataError):
            return apps.AppLeaf(init_path=obj)

    return files.FileLeaf(obj)


class DirectorySource(Source, FilesystemWatchMixin):
    def __init__(
        self,
        directory: str,
        show_hidden: bool = False,
        *,
        toplevel: bool = False,
    ) -> None:
        # Use glib filename reading to make display name out of filenames
        # this function returns a `unicode` object
        name = GLib.filename_display_basename(directory)
        super().__init__(name)
        self._directory = directory
        self._show_hidden = show_hidden
        self._toplevel = toplevel
        self.monitor: ty.Any = None
        self._user_home = os.path.expanduser("~")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}"
            f'("{self._directory}", show_hidden={self._show_hidden})'
        )

    def initialize(self) -> None:
        # only toplevel directories are active monitored
        if self._toplevel:
            self.monitor = self.monitor_directories(self._directory)

    def finalize(self) -> None:
        if self.monitor:
            self.stop_monitor_fs_changes(self.monitor)
            self.monitor = None

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        return self._show_hidden or not gfile.get_basename().startswith(".")

    def get_items(self) -> ty.Iterator[Leaf]:
        try:
            dirfiles: ty.Iterable[str] = os.listdir(self._directory)
        except OSError as exc:
            self.output_error(exc)
        else:
            if not self._show_hidden:
                dirfiles = (f for f in dirfiles if f[0] != ".")

            yield from (
                construct_file_leaf(path.join(self._directory, fname))
                for fname in dirfiles
            )

    def should_sort_lexically(self) -> bool:
        return True

    def _parent_path(self) -> str:
        return path.normpath(path.join(self._directory, path.pardir))

    def has_parent(self) -> bool:
        return not path.samefile(self._directory, self._parent_path())

    def get_parent(self) -> DirectorySource | None:
        if not self.has_parent():
            return None

        return DirectorySource(self._parent_path())

    def get_description(self) -> str:
        return _("Directory source %s") % self._directory

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        return icons.get_gicon_for_file(self._directory)

    def get_icon_name(self) -> str:
        return "folder"

    def get_leaf_repr(self) -> Leaf | None:
        alias = None
        directory = self._directory
        if os.path.isdir(directory) and os.path.samefile(
            directory, self._user_home
        ):
            alias = _("Home Folder")

        return files.FileLeaf(directory, alias=alias)

    def provides(self) -> ty.Iterable[ty.Type[Leaf]]:
        yield files.FileLeaf
        yield apps.AppLeaf


class FileSource(Source):
    def __init__(self, dirlist: list[str], depth: int = 0) -> None:
        """
        @dirlist: Directories as byte strings
        """
        name = GLib.filename_display_basename(dirlist[0])
        if len(dirlist) > 1:
            name = _("%s et. al.") % name

        super().__init__(name)
        self.dirlist = dirlist
        self.depth = depth

    def __repr__(self) -> str:
        mod = self.__class__.__module__
        cname = self.__class__.__name__
        dirs = ", ".join(f'"{d}"' for d in sorted(self.dirlist))
        return f"{mod}.{cname}(({dirs}, ), depth={self.depth})"

    def get_items(self) -> ty.Iterable[Leaf]:
        for directory in self.dirlist:
            dirfiles = fileutils.get_dirlist(
                directory, max_depth=self.depth, exclude=self._exclude_file
            )
            yield from map(construct_file_leaf, dirfiles)

    def should_sort_lexically(self) -> bool:
        return True

    def _exclude_file(self, filename: str) -> bool:
        return filename.startswith(".")

    def get_description(self) -> str:
        return _("Recursive source of %(dir)s, (%(levels)d levels)") % {
            "dir": self.name,
            "levels": self.depth,
        }

    def get_icon_name(self) -> str:
        return "folder-saved-search"

    def provides(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield files.FileLeaf
        yield apps.AppLeaf
