__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource",)
__kupfer_actions__ = ()
__description__ = _("Index of Firefox bookmarks")
__version__ = "2020.1"
__author__ = "Ulrik, William Friesen, Karol Będkowski"

import itertools
import os
import sqlite3
import time
from contextlib import closing

from kupfer import plugin_support
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.objects import Source, UrlLeaf

from ._firefox_support import get_firefox_home_file, get_ffdb_conn_str

MAX_ITEMS = 10000

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "profile",
        "label": _("Firefox profile name or path"),
        "type": str,
        "value": "",
    },
)

_BOOKMARKS_SQL = """
SELECT moz_places.url, moz_bookmarks.title
FROM moz_places, moz_bookmarks
WHERE moz_places.id = moz_bookmarks.fk
    AND moz_bookmarks.keyword_id IS NULL
ORDER BY visit_count DESC
LIMIT ?"""


class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("firefox", "firefox-esr")

    def __init__(self):
        self.monitor_token = None
        super().__init__(_("Firefox Bookmarks"))
        self._version = 3

    def initialize(self):
        if ff_home := get_firefox_home_file(""):
            self.monitor_token = self.monitor_directories(str(ff_home))

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "lock"

    def _get_ffx3_bookmarks(self):
        """Query the firefox places bookmark database"""
        fpath = get_ffdb_conn_str(
            __kupfer_settings__["profile"], "places.sqlite"
        )
        if not fpath:
            return []

        for _ in range(2):
            try:
                self.output_debug("Reading bookmarks from", fpath)
                with closing(
                    sqlite3.connect(fpath, uri=True, timeout=1)
                ) as conn:
                    cur = conn.cursor()
                    cur.execute(_BOOKMARKS_SQL, (MAX_ITEMS,))
                    return list(itertools.starmap(UrlLeaf, cur))
            except sqlite3.Error as err:
                # Something is wrong with the database
                # wait short time and try again
                self.output_debug("Read bookmarks error:", str(err))
                time.sleep(1)

        self.output_exc()
        return []

    def get_items(self):
        return self._get_ffx3_bookmarks()

    def get_description(self):
        return _("Index of Firefox bookmarks")

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
