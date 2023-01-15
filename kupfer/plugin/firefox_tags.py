__kupfer_name__ = _("Firefox Tags")
__kupfer_sources__ = ("TagsSource",)
__description__ = _("Browse Firefox bookmarks by tags")
__version__ = "2021-09-05"
__author__ = "Karol Będkowski"

import itertools
import sqlite3
import time
from contextlib import closing

from kupfer import plugin_support
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.objects import Leaf, Source, UrlLeaf

from ._firefox_support import get_firefox_home_file, get_ffdb_conn_str

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "profile",
        "label": _("Firefox profile name or path"),
        "type": str,
        "value": "",
    },
)


MAX_ITEMS = 10000


class FirefoxTag(Leaf):
    def get_icon_name(self):
        return "text-html"

    def has_content(self):
        return True

    def content_source(self, alternate=False):
        return TagBookmarksSource(self.object, self.name)


_TAGS_SQL = """
SELECT id, title
FROM moz_bookmarks mb
WHERE mb.parent = 4
    AND mb.fk IS NULL
"""


class TagsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("firefox", "firefox-esr")

    def __init__(self):
        super().__init__(_("Firefox Tags"))
        self.monitor_token = None

    def initialize(self):
        profile = __kupfer_settings__["profile"]
        if ff_home := get_firefox_home_file("", profile):
            self.monitor_token = self.monitor_directories(str(ff_home))

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "lock"

    def get_items(self):
        """Get tags from firefox places database"""
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
                    cur.execute(_TAGS_SQL)
                    return list(itertools.starmap(FirefoxTag, cur))

            except sqlite3.Error as err:
                self.output_debug("Read bookmarks error:", str(err))
                # Something is wrong with the database
                # wait short time and try again
                time.sleep(1)

        self.output_exc()
        return []

    def get_description(self):
        return _("Index of Firefox bookmarks by tags")

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield FirefoxTag


_TAG_BOOKMARKS_SQL = """
SELECT mp.url, mp.title
FROM moz_places mp
JOIN moz_bookmarks mb ON mp.id = mb.fk
WHERE mb.keyword_id IS NULL
	AND mb.parent = ?
ORDER BY visit_count DESC
LIMIT ?"""


class TagBookmarksSource(Source):
    def __init__(self, tag_id: int, tag: str):
        super().__init__(_("Firefox Bookmarks by tag"))
        self.tag = tag
        self.tag_id = tag_id

    def get_items(self):
        """Query the firefox places database for bookmarks with tag"""

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
                    cur.execute(_TAG_BOOKMARKS_SQL, (self.tag_id, MAX_ITEMS))
                    return list(itertools.starmap(UrlLeaf, cur))
            except sqlite3.Error as err:
                # Something is wrong with the database
                # wait short time and try again
                self.output_debug("Read bookmarks error:", str(err))
                time.sleep(1)

        self.output_exc()
        return []

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
