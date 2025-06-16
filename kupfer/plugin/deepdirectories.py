"""
Changes:
    2018-09-04 * fix: Python 3 compatibility
    2012-10-08 * fix: errors when no one configured directories exists
    2012-06-09 + max depth; fix source name
    2012-06-08 - init
"""

__kupfer_name__ = _("Deep Directories")
__kupfer_sources__ = ("DeepDirSource",)
__description__ = _("Recursive index directories")
__version__ = "2018-09-04"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import typing as ty

from kupfer import plugin_support
from kupfer.obj import apps, files
from kupfer.obj.base import Leaf, Source
from kupfer.obj.filesrc import construct_file_leaf
from kupfer.support import fileutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "dirs",
        "label": _("Directories:"),
        "type": list,
        "helper": "choose_directory",
        "value": ["~/Documents/"],
    },
    {
        "key": "depth",
        "label": _("Depth (max 10):"),
        "type": int,
        "value": 2,
        "max": 10,
        "min": 1,
    },
)


_MAX_DEPTH = 10


class DeepDirSource(Source):
    source_use_cache = False

    def __init__(self, name : str=_("Deep Directories")) -> None:
        super().__init__(name)
        self.dirs : list[str] = []
        self.depth = 1

    def initialize(self) -> None:
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._on_setting_changed
        )
        self.dirs = list(self._get_dirs())
        self.depth = min(__kupfer_settings__["depth"], _MAX_DEPTH)

    def get_items(self) -> ty.Iterable[Leaf]:
        for directory in self.dirs:
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
            "dir": ",".join(self.dirs),
            "levels": self.depth,
        }

    def get_icon_name(self) -> str:
        return "folder-saved-search"

    def provides(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield files.FileLeaf
        yield apps.AppLeaf

    @staticmethod
    def _get_dirs() -> ty.Generator[str]:
        for path in __kupfer_settings__["dirs"] or ():
            if (path := os.path.expanduser(path.strip())) and os.path.isdir(
                path
            ):
                yield path

    def _on_setting_changed(self, settings, key, value):
        if key in ("dirs", "depth"):
            self.dirs = list(self._get_dirs())
            self.depth = min(__kupfer_settings__["depth"], _MAX_DEPTH)
            self.mark_for_update()
