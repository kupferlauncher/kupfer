from __future__ import annotations

__kupfer_name__ = _("Search the Web")
__kupfer_sources__ = ("OpenSearchSource",)
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("SearchFor", "SearchWithEngine")
__description__ = _(
    "Search the web with OpenSearch and user defined search engines"
)
__version__ = "2023-05-01"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, KB"

import locale
import os
import typing as ty
import urllib.parse
from pathlib import Path
from xml.etree import ElementTree

from kupfer import config, launch, plugin_support
from kupfer.obj import Action, Leaf, Source, TextLeaf
from kupfer.plugin._firefox_support import get_firefox_home_file

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "extra_engines",
        "label": _("User search engines:"),
        "type": str,
        "multiline": True,
        "value": "https://www.qwant.com/?q=%s\n"
        "https://search.brave.com/search?q=%s",
        "tooltip": _(
            "Define URLs for search engines; '%s' is replaced by "
            "search term."
        ),
    },
)


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
    terms = _urlencode(terms)
    if "{searchTerms}" in search_url:
        query_url = search_url.replace("{searchTerms}", terms)
    else:
        query_url = search_url.replace("%s", terms)

    launch.show_url(query_url)


def _get_custom_engine_name(url: str) -> str | None:
    if not url:
        return None

    components = urllib.parse.urlparse(url)
    if netloc := components.netloc:
        return (
            netloc.removeprefix("www.")
            .removesuffix(".com")
            .replace(".", " ")
            .capitalize()
        )

    return None


class SearchWithEngine(Action):
    """TextLeaf -> SearchWithEngine -> SearchEngine"""

    action_accelerator = "s"

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

    action_accelerator = "s"

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


class OpenSearchParseError(Exception):
    pass


def gettagname(tag):
    return tag.rsplit("}", 1)[-1]


def _get_plugin_dirs() -> ty.Iterator[Path]:
    """Get all posible plugins path (may not exists)"""
    # accept in kupfer data dirs
    yield from map(Path, config.get_data_dirs("searchplugins"))

    # firefox in home directory
    if ffx_home := get_firefox_home_file("searchplugins"):
        yield ffx_home

    yield from map(
        Path, config.get_data_dirs("searchplugins", package="firefox")
    )
    yield from map(
        Path, config.get_data_dirs("searchplugins", package="iceweasel")
    )

    suffixes = ["en-US"]
    if cur_lang := locale.getlocale(locale.LC_MESSAGES)[0]:
        suffixes = [cur_lang.replace("_", "-"), cur_lang[:2]] + suffixes

    addon_dir = Path("/usr/lib/firefox-addons/searchplugins")
    for suffix in suffixes:
        if (addon_lang_dir := addon_dir.joinpath(suffix)).exists():
            yield addon_lang_dir
            break

    # debian iceweasel
    yield Path("/etc/iceweasel/searchplugins/common")

    for suffix in suffixes:
        yield Path("/etc/iceweasel/searchplugins/locale", suffix)

    # try to find all versions of firefox
    for prefix in ("/usr/lib", "/usr/share"):
        for dirname in os.listdir(prefix):
            if dirname.startswith(("firefox", "iceweasel")):
                yield Path(prefix, dirname, "searchplugins")
                yield Path(
                    prefix, dirname, "distribution", "searchplugins", "common"
                )


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
                params = tuple(
                    (ch.get("name"), ch.get("value"))
                    for ch in child
                    if gettagname(ch.tag) == "Param"
                )
                if params:
                    text += _noescape_urlencode(params)
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

    def initialize(self):
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._setting_changed
        )

    def _setting_changed(self, settings, key, value):
        self.mark_for_update()

    def _parse_opensearch(self, path: str) -> dict[str, ty.Any] | None:
        try:
            etree = ElementTree.parse(path)
            return _parse_etree(etree, name=path)  # type:ignore
        except Exception as exc:
            self.output_debug(f"{type(exc).__name__}: {exc}")

        return None

    def get_items(self) -> ty.Iterator[SearchEngine]:
        # files are unique by filename to allow override
        visited_files = set()
        for pdir in _get_plugin_dirs():
            if not pdir.is_dir():
                continue

            self.output_debug("Processing searchplugins dir", pdir)

            for fname in os.listdir(pdir):
                if fname in visited_files:
                    continue

                visited_files.add(fname)
                fpath = pdir.joinpath(fname)
                if not fpath.is_dir():
                    if search := self._parse_opensearch(str(fpath)):
                        yield SearchEngine(search, search["ShortName"])

        # add user search engines
        if custom_ses := __kupfer_settings__["extra_engines"]:
            for url in custom_ses.replace(";", "\n").split():
                url = url.strip()
                if url and (name := _get_custom_engine_name(url)):
                    yield SearchEngine({"Url": url, "Description": url}, name)

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield SearchEngine

    def get_icon_name(self):
        return "applications-internet"
