# encoding: utf-8


__kupfer_name__ = _("Vivaldi Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__kupfer_actions__ = ()
__description__ = _("Index of Vivaldi bookmarks")
__version__ = "2017.1"
__author__ = "thorko"

#from configparser import RawConfigParser
#from contextlib import closing
import os
import json
#from urllib.parse import quote, urlparse

from kupfer import plugin_support
from kupfer.objects import Source, Action, Leaf
from kupfer.objects import UrlLeaf, TextLeaf, TextSource
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.objects import OpenUrl
from kupfer import utils

MAX_ITEMS = 10000

class BookmarksSource (AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("vivaldi")
    def __init__(self):
        super().__init__(_("Vivaldi Bookmarks"))
        self._version = 3

    def initialize(self):
        vivaldi_dir = os.path.expanduser("~/.config/vivaldi/Default")
        self.monitor_token = self.monitor_directories(vivaldi_dir)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == 'lock'

    def _get_vivaldi_bookmarks(self):
        """Query the vivaldi places bookmark database"""
        bookmark = []
        bookmarks_file = os.path.expanduser("~/.config/vivaldi/Default/Bookmarks")
        data = json.loads(open(bookmarks_file, encoding='utf-8').read())
        for c in data['roots']['bookmark_bar']['children']:
            if 'children' in c:
                for l in c['children']:
                    if 'children' in l:
                        for k in l['children']:
                            if 'url' in k:
                                bookmark.append({'title': k['name'], 'url': k['url']})
                    if 'url' in l:
                        bookmark.append({'title': l['name'], 'url': l['url']})

        return[UrlLeaf(b['url'], b['title'].strip('/')) for b in bookmark]

    def get_items(self):
        return self._get_vivaldi_bookmarks()

    def get_description(self):
        return _("Index of Vivaldi bookmarks")

    def get_gicon(self):
        return self.get_leaf_repr() and self.get_leaf_repr().get_gicon()

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
