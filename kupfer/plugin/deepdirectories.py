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

from kupfer import plugin_support
from kupfer.obj import sources


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "dirs",
        "label": _("Directories (;-separated):"),
        "type": str,
        "value": "~/Documents/",
    },
    {
        "key": "depth",
        "label": _("Depth (max 10):"),
        "type": int,
        "value": 2,
    },
)

MAX_DEPTH = 10


class DeepDirSource(sources.FileSource):
    def __init__(self, name=_("Deep Directories")):
        sources.FileSource.__init__(
            self,
            self._get_dirs() or [""],
            min(__kupfer_settings__["depth"], MAX_DEPTH),
        )
        self.name = name

    def initialized(self):
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._setting_changed
        )

    def get_items(self):
        self.dirlist = self._get_dirs()
        if not self.dirlist:
            return []

        self.depth = min(__kupfer_settings__["depth"], MAX_DEPTH)
        return sources.FileSource.get_items(self)

    @staticmethod
    def _get_dirs():
        if not __kupfer_settings__["dirs"]:
            return []

        return list(
            filter(
                os.path.isdir,
                (
                    os.path.expanduser(path)
                    for path in __kupfer_settings__["dirs"].split(";")
                ),
            )
        )

    def _setting_changed(self, settings, key, value):
        if key in ("dirs", "depth"):
            self.mark_for_update()
