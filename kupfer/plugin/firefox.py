__kupfer_name__ = _("Firefox Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_actions__ = ()
__description__ = _("Index of Firefox bookmarks")
__version__ = "2019.1"
__author__ = "Ulrik Sverdrup, William Friesen, Karol Będkowski, Dario Seidl"

from configparser import RawConfigParser
from contextlib import closing
import os
import sqlite3
from urllib.parse import quote, urlparse
from shutil import copy2
from tempfile import gettempdir

from kupfer import plugin_support
from kupfer.objects import Source, Action, Leaf
from kupfer.objects import UrlLeaf, TextLeaf, TextSource
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.objects import OpenUrl
from kupfer import utils

MAX_ITEMS = 10000

class BookmarksSource (AppLeafContentMixin, Source, FilesystemWatchMixin):
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
        fpath = get_firefox_home_file("places.sqlite")
        if not (fpath and os.path.isfile(fpath)):
            return []
        tmp = gettempdir()
        tmpd = os.path.join(tmp, "kupfer")
        if not os.path.exists(tmpd):
            os.makedirs(tmpd)
        tmpfpath = os.path.join(tmpd, "places.sqlite")
        if not os.path.isfile(tmpfpath):
            copy2(fpath, tmpfpath)
        try:
            copy2(fpath, tmpfpath)
            self.output_debug("Reading bookmarks from", tmpfpath)
            with closing(sqlite3.connect(tmpfpath, timeout=1)) as conn:
                c = conn.cursor()
                c.execute("""SELECT moz_places.url, moz_bookmarks.title
                             FROM moz_places, moz_bookmarks
                             WHERE moz_places.id = moz_bookmarks.fk
                                AND moz_bookmarks.keyword_id IS NULL
                             ORDER BY visit_count DESC
                             LIMIT ?""",
                             (MAX_ITEMS, ))
                return [UrlLeaf(url, title) for url, title in c]
        except sqlite3.Error:
            # Something is wrong with the database
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

def get_firefox_home_file(needed_file):
    firefox_dir = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(firefox_dir):
        return None

    config = RawConfigParser({"Default" : 0})
    config.read(os.path.join(firefox_dir, "profiles.ini"))
    path = None

    for section in config.sections():
        if config.has_option(section, "Default") and config.get(section, "Default") == "1":
            path = config.get (section, "Path")
            break
        elif path == None and config.has_option(section, "Path"):
            path = config.get (section, "Path")

    if path == None:
        return ""

    if path.startswith("/"):
        return os.path.join(path, needed_file)

    return os.path.join(firefox_dir, path, needed_file)
