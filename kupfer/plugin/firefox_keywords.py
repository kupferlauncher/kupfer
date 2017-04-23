__kupfer_name__ = _("Firefox Keywords")
__kupfer_sources__ = ("KeywordsSource", )
__kupfer_text_sources__ = ("KeywordSearchSource", )
__kupfer_actions__ = ("SearchWithEngine", )
__description__ = _("Search the web with Firefox keywords")
__version__ = "2017.1"
__author__ = ""

from configparser import RawConfigParser
from contextlib import closing
import os
import sqlite3
from urllib.parse import quote, urlparse

from kupfer import plugin_support
from kupfer.objects import Source, Action, Leaf
from kupfer.objects import TextLeaf, TextSource
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.objects import OpenUrl, RunnableLeaf
from kupfer import utils
from kupfer import config, plugin_support

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "default",
        "label": _("Default for ?"),
        "type": str,
        "value": 'https://www.google.com/search?ie=UTF-8&q=%s',
    }
)

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

def _url_domain(text):
    components = list(urlparse(text))
    domain = "".join(components[1:2])
    return domain

class Keyword(Leaf):
    def __init__(self, title, kw, url):
        title = title if title else _url_domain(url)
        name = "%s (%s)" % (kw, title)
        super().__init__(url, name)
        self.keyword = kw

    def _is_search(self):
        return "%s" in self.object

    def get_actions(self):
        if self._is_search():
            yield SearchFor()
        else:
            yield OpenUrl()

    def get_description(self):
        return self.object

    def get_icon_name(self):
        return "text-html"

    def get_text_representation(self):
        return self.object

class KeywordsSource (Source, FilesystemWatchMixin):
    instance = None
    def __init__(self):
        super().__init__(_("Firefox Keywords"))

    def initialize(self):
        KeywordsSource.instance = self
        ff_home = get_firefox_home_file('')
        self.monitor_token = self.monitor_directories(ff_home)

    def finalize(self):
        KeywordsSource.instance = None

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == 'lock'

    def _get_ffx3_bookmarks(self):
        """Query the firefox places bookmark database"""
        fpath = get_firefox_home_file("places.sqlite")
        if not (fpath and os.path.isfile(fpath)):
            return []
        try:
            self.output_debug("Reading bookmarks from", fpath)
            with closing(sqlite3.connect(fpath, timeout=1)) as conn:
                c = conn.cursor()
                c.execute("""SELECT moz_places.url, moz_places.title, moz_keywords.keyword
                             FROM moz_places, moz_keywords
                             WHERE moz_places.id = moz_keywords.place_id
                             """)
                return [Keyword(title, kw,  url) for url, title, kw in c]
        except sqlite3.Error:
            # Something is wrong with the database
            self.output_exc()
            return []

    def get_items(self):
        seen_keywords = set()
        for kw in self._get_ffx3_bookmarks():
            seen_keywords.add(kw.keyword)
            yield kw

    def get_description(self):
        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield Keyword

class SearchWithEngine (Action):
    """TextLeaf -> SearchWithEngine -> Keyword"""
    action_accelerator = "s"
    def __init__(self):
        Action.__init__(self, _("Search With..."))

    def activate(self, leaf, iobj):
        url = iobj.object
        _do_search_engine(leaf.object, url)

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield Keyword

    def valid_object(self, obj, for_item):
        return obj._is_search()

    def object_source(self, for_item=None):
        return KeywordsSource()

    def get_description(self):
        return _("Search the web with Firefox keywords")

    def get_icon_name(self):
        return "edit-find"

class SearchFor (Action):
    """Keyword -> SearchFor -> TextLeaf

    This is the opposite action to SearchWithEngine
    """
    action_accelerator = "s"
    def __init__(self):
        Action.__init__(self, _("Search For..."))

    def activate(self, leaf, iobj):
        url = leaf.object
        terms = iobj.object
        _do_search_engine(terms, url)

    def item_types(self):
        yield Keyword

    def requires_object(self):
        return True

    def object_types(self):
        yield TextLeaf

    def object_source(self, for_item):
        return TextSource(placeholder=_("Search Terms"))

    def valid_object(self, obj, for_item):
        # NOTE: Using exact class to skip subclasses
        return type(obj) == TextLeaf

    def get_description(self):
        return _("Search the web with Firefox keywords")

    def get_icon_name(self):
        return "edit-find"

class KeywordSearchSource(TextSource):
    def __init__(self):
        super().__init__(_("Firefox Keywords (?-source)"))

    def get_text_items(self, text):
        if not text.startswith("?"):
            return
        parts = text[1:].split(maxsplit=1)
        if len(parts) < 1:
            return
        query = parts[1] if len(parts) > 1 else ""
        for kw in KeywordsSource.instance.get_leaves():
            if kw._is_search() and kw.keyword == parts[0]:
                yield SearchWithKeyword(kw, query)
                return
        default = __kupfer_settings__['default'].strip()
        if default:
            if '%s' not in default:
                default += '%s'
            yield SearchWithKeyword(Keyword(None, "", default), text[1:])

    def get_description(self):
        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield SearchWithKeyword

    def get_rank(self):
        return 80

class SearchWithKeyword(RunnableLeaf):
    def __init__(self, keyword, text):
        super().__init__((keyword, text), _('Search for "%s"') % (text, ))

    def run(self):
        kw = self.keyword_leaf
        _do_search_engine(self.query, kw.object)

    @property
    def keyword_leaf(self):
        return self.object[0]

    @property
    def query(self):
        return self.object[1]

    def get_icon_name(self):
        return "web-browser"

    def get_description(self):
        return _("Search using %s") % self.keyword_leaf

    def get_text_representation(self):
        kw = self.keyword_leaf
        return _query_url(self.query, kw.object)

def _do_search_engine(terms, search_url, encoding="UTF-8"):
    """Show an url searching for @search_url with @terms"""
    utils.show_url(_query_url(terms, search_url))

def _query_url(terms, search_url):
    """Show an url searching for @search_url with @terms"""
    query_url = search_url.replace("%s", quote(terms))
    return query_url

