__kupfer_name__ = _("Librewolf Bookmarks")
__kupfer_sources__ = ("BookmarksSource",)
__kupfer_actions__ = ()
__description__ = _(
    "Index of Librewolf bookmarks. "
    "Bookmark is always opened in default browser."
)
__version__ = "2023.1"
__author__ = "Ulrik, William Friesen, Karol Będkowski"

from gettext import gettext as _

from kupfer import plugin_support
from kupfer.obj import Source, UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.plugin._firefox_support import (
    get_bookmarks,
    get_librewolf_home_file,
)


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "profile",
        "label": _("Librewolf profile name or path"),
        "type": str,
        "value": "",
        "helper": "choose_directory",
    },
)


class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = "librewolf"
    source_scan_interval: int = 3600

    def __init__(self):
        self.monitor_token = None
        super().__init__(_("Librewolf Bookmarks"))
        self._version = 3

    def initialize(self):
        if ff_home := get_librewolf_home_file(""):
            self.monitor_token = self.monitor_directories(str(ff_home))

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "lock"

    def mark_for_update(self, postpone=False):
        super().mark_for_update(postpone=True)

    def _get_ffx3_bookmarks(self):
        """Query the librewolf places bookmark database"""
        fpath = get_librewolf_home_file(
            "places.sqlite", __kupfer_settings__["profile"]
        )

        return get_bookmarks(fpath)

    def get_items(self):
        return self._get_ffx3_bookmarks()

    def get_description(self):
        return _("Index of Librewolf bookmarks")

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
