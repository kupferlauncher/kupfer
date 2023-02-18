__kupfer_name__ = _("Search the Web")
__kupfer_sources__ = ("OpenSearchSource",)
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
    "SearchFor",
    "SearchWithEngine",
)
__description__ = _("Search the web with OpenSearch search engines")
__version__ = "2020-04-19"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import locale
import os
import typing as ty
import urllib.parse
from pathlib import Path
from xml.etree import ElementTree

from kupfer import config, utils
from kupfer.objects import Action, Leaf, Source, TextLeaf
from kupfer.plugin._firefox_support import get_firefox_home_file


def _noescape_urlencode(items):
    """Assemble an url param string from @items, without
    using any url encoding.
    """
    return "?" + "&".join(f"{n}={v}" for n, v in items)


def _urlencode(word):
    """Urlencode a single string of bytes @word"""
    return urllib.parse.urlencode({"q": word})[2:]


def _do_search_engine(terms, search_url, encoding="UTF-8"):
    """Show an url searching for @search_url with @terms"""
    query_url = search_url.replace("{searchTerms}", _urlencode(terms))
    utils.show_url(query_url)


class SearchWithEngine(Action):
    """TextLeaf -> SearchWithEngine -> SearchEngine"""

    def __init__(self):
        Action.__init__(self, _("Search With..."))

    def activate(self, leaf, iobj=None, ctx=None):
        coding = iobj.object.get("InputEncoding")
        url = iobj.object["Url"]
        _do_search_engine(leaf.object, url, encoding=coding)

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield SearchEngine

    def object_source(self, for_item=None):
        return OpenSearchSource()

    def get_description(self):
        return _("Search the web with OpenSearch search engines")

    def get_icon_name(self):
        return "edit-find"


class SearchFor(Action):
    """SearchEngine -> SearchFor -> TextLeaf

    This is the opposite action to SearchWithEngine
    """

    def __init__(self):
        Action.__init__(self, _("Search For..."))

    def activate(self, leaf, iobj=None, ctx=None):
        coding = leaf.object.get("InputEncoding")
        url = leaf.object["Url"]
        terms = iobj.object
        _do_search_engine(terms, url, encoding=coding)

    def item_types(self):
        yield SearchEngine

    def requires_object(self):
        return True

    def object_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search the web with OpenSearch search engines")

    def get_icon_name(self):
        return "edit-find"


class SearchEngine(Leaf):
    def get_description(self):
        desc = self.object.get("Description")
        return desc if desc != str(self) else None

    def get_icon_name(self):
        return "text-html"


def coroutine(func):
    """Coroutine decorator: Start the coroutine"""

    def startcr(*ar, **kw):
        cr = func(*ar, **kw)
        next(cr)
        return cr

    return startcr


class OpenSearchParseError(Exception):
    pass


def gettagname(tag):
    return tag.rsplit("}", 1)[-1]


def _get_plugin_dirs() -> ty.Iterator[str]:
    # accept in kupfer data dirs
    yield from config.get_data_dirs("searchplugins")

    # firefox in home directory
    ffx_home = get_firefox_home_file("searchplugins")
    if ffx_home and ffx_home.is_dir():
        yield str(ffx_home)

    yield from config.get_data_dirs("searchplugins", package="firefox")
    yield from config.get_data_dirs("searchplugins", package="iceweasel")

    addon_dir = Path("/usr/lib/firefox-addons/searchplugins")
    cur_lang, _ignored = locale.getlocale(locale.LC_MESSAGES)
    suffixes = ["en-US"]
    if cur_lang:
        suffixes = [cur_lang.replace("_", "-"), cur_lang[:2]] + suffixes

    for suffix in suffixes:
        if (addon_lang_dir := addon_dir.joinpath(suffix)).exists():
            yield str(addon_lang_dir)
            break

    # debian iceweasel
    if Path("/etc/iceweasel/searchplugins/common").is_dir():
        yield "/etc/iceweasel/searchplugins/common"

    for suffix in suffixes:
        addon_path = Path("/etc/iceweasel/searchplugins/locale", suffix)
        if addon_path.is_dir():
            yield str(addon_path)

    # try to find all versions of firefox
    for prefix in ("/usr/lib", "/usr/share"):
        for dirname in os.listdir(prefix):
            if dirname.startswith("firefox") or dirname.startswith("iceweasel"):
                addon_dir = Path(prefix, dirname, "searchplugins")
                if addon_dir.is_dir():
                    yield str(addon_dir)

                addon_dir = Path(
                    prefix,
                    dirname,
                    "distribution",
                    "searchplugins",
                    "common",
                )
                if addon_dir.is_dir():
                    yield str(addon_dir)


_OS_VITAL_KEYS = {"Url", "ShortName"}
_OS_KEYS = ("Description", "Url", "ShortName", "InputEncoding")
_OS_ROOTS = ("OpenSearchDescription", "SearchPlugin")


def _parse_etree(etree, name=None):
    if gettagname(etree.getroot().tag) not in _OS_ROOTS:
        raise OpenSearchParseError(f"Search {name} has wrong type")

    search = {}
    for child in etree.getroot():
        tagname = gettagname(child.tag)
        if tagname not in _OS_KEYS:
            continue

        # Only pick up Url tags with type="text/html"
        if tagname == "Url":
            if child.get("type") == "text/html" and child.get("template"):
                text = child.get("template")
                params = {
                    ch.get("name"): ch.get("value")
                    for ch in child
                    if gettagname(ch.tag) == "Param"
                }
                if params:
                    text += _noescape_urlencode(list(params.items()))
            else:
                continue

        else:
            text = (child.text or "").strip()

        search[tagname] = text

    if not _OS_VITAL_KEYS.issubset(list(search.keys())):
        raise OpenSearchParseError(f"Search {name} missing _OS_KEYS")

    return search


class OpenSearchSource(Source):
    def __init__(self):
        Source.__init__(self, _("Search Engines"))

    @coroutine
    def _parse_opensearch(self, target):
        """This is a coroutine to parse OpenSearch files"""
        while True:
            try:
                path = yield
                etree = ElementTree.parse(path)
                target.send(_parse_etree(etree, name=path))
            except Exception as exc:
                self.output_debug(f"{type(exc).__name__}: {exc}")

    def get_items(self):
        plugin_dirs = list(_get_plugin_dirs())
        self.output_debug(
            "Found following searchplugins directories", sep="\n", *plugin_dirs
        )

        @coroutine
        def collect(seq):
            """Collect items in list @seq"""
            while True:
                seq.append((yield))

        searches: list[dict[str, ty.Any]] = []
        collector = collect(searches)
        parser = self._parse_opensearch(collector)
        # files are unique by filename to allow override
        visited_files = set()
        for pdir in plugin_dirs:
            try:
                for fname in os.listdir(pdir):
                    if fname in visited_files:
                        continue

                    fpath = os.path.join(pdir, fname)
                    if not os.path.isdir(fpath):
                        parser.send(fpath)
                        visited_files.add(fname)

            except OSError as exc:
                self.output_error(exc)

        yield from (SearchEngine(s, s["ShortName"]) for s in searches)

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield SearchEngine

    def get_icon_name(self):
        return "applications-internet"
