__kupfer_name__ = _("Firefox Tags")
__kupfer_sources__ = ("TagsSource",)
__description__ = _("Browse Firefox bookmarks by tags")
__version__ = "2021-09-05"
__author__ = "Karol Będkowski"

import itertools
import typing as ty

from kupfer import plugin_support
from kupfer.obj import Leaf, Source, UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.plugin._firefox_support import get_firefox_home_file, query_database

if ty.TYPE_CHECKING:
    from gettext import gettext as _

MAX_ITEMS = 10000

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "profile",
        "label": _("Firefox profile name or path"),
        "type": str,
        "value": "",
        "helper": "choose_directory",
    },
)


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
    source_scan_interval: int = 3600

    def __init__(self):
        super().__init__(_("Firefox Tags"))
        self.monitor_token = None

    def initialize(self):
        profile = __kupfer_settings__["profile"]
        if ff_home := get_firefox_home_file("", profile):
            self.monitor_token = self.monitor_directories(str(ff_home))

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "lock"

    def mark_for_update(self, postpone=False):
        super().mark_for_update(postpone=True)

    def get_items(self):
        """Get tags from firefox places database"""
        fpath = get_firefox_home_file(
            "places.sqlite", __kupfer_settings__["profile"]
        )
        if not fpath:
            return []

        return list(
            itertools.starmap(FirefoxTag, query_database(str(fpath), _TAGS_SQL))
        )

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
        fpath = get_firefox_home_file(
            "places.sqlite", __kupfer_settings__["profile"]
        )
        if not fpath:
            return []

        return list(
            itertools.starmap(
                UrlLeaf,
                query_database(
                    str(fpath), _TAG_BOOKMARKS_SQL, (self.tag_id, MAX_ITEMS)
                ),
            )
        )

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
