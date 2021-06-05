__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_actions__ = ()
__description__ = _("Index of Firefox bookmarks")
__version__ = "2020.1"
__author__ = "Ulrik, William Friesen, Karol Będkowski"

from contextlib import closing
import os
import sqlite3
import time

from kupfer.objects import Source
from kupfer.objects import UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer import plugin_support

from ._firefox_support import get_firefox_home_file

MAX_ITEMS = 10000

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "profile",
        "label": _("Firefox profile name or path"),
        "type": str,
        "value": "",
    },
)


class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("firefox", "firefox-esr")
    def __init__(self):
        super().__init__(_("Firefox Bookmarks"))
        self._version = 3

    def initialize(self):
        ff_home = get_firefox_home_file('')
        self.monitor_token = self.monitor_directories(ff_home)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == 'lock'

    def _get_ffx3_bookmarks(self):
        """Query the firefox places bookmark database"""
        profile = __kupfer_settings__["profile"]
        fpath = get_firefox_home_file("places.sqlite", profile)
        if not (fpath and os.path.isfile(fpath)):
            return []

        fpath = fpath.replace("?", "%3f").replace("#", "%23")
        fpath = "file:" + fpath + "?immutable=1&mode=ro"

        for _ in range(2):
            try:
                self.output_debug("Reading bookmarks from", fpath)
                with closing(sqlite3.connect(fpath, uri=True,
                                             timeout=1)) as conn:
                    c = conn.cursor()
                    c.execute("""SELECT moz_places.url, moz_bookmarks.title
                              FROM moz_places, moz_bookmarks
                              WHERE moz_places.id = moz_bookmarks.fk
                                    AND moz_bookmarks.keyword_id IS NULL
                              ORDER BY visit_count DESC
                              LIMIT ?""",
                              (MAX_ITEMS, ))
                    return [UrlLeaf(url, title) for url, title in c]
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
        return self.get_leaf_repr() and self.get_leaf_repr().get_gicon()

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
