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
from kupfer.obj.filesrc import FileSource

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


class DeepDirSource(FileSource):
    def __init__(self, name=_("Deep Directories")):
        FileSource.__init__(
            self,
            [""],
            min(__kupfer_settings__["depth"], _MAX_DEPTH),
        )
        self.name = name

    def initialize(self):
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._on_setting_changed
        )

    def get_items(self):
        self.dirlist = list(self._get_dirs())
        self.depth = min(__kupfer_settings__["depth"], _MAX_DEPTH)
        yield from FileSource.get_items(self)

    @staticmethod
    def _get_dirs():
        dirs = __kupfer_settings__["dirs"]
        for path in dirs or ():
            if (path := os.path.expanduser(path.strip())) and os.path.isdir(
                path
            ):
                yield path

    def _on_setting_changed(self, settings, key, value):
        if key in ("dirs", "depth"):
            self.mark_for_update()
