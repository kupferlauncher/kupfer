import os
import urllib.parse
import urllib.request, urllib.parse, urllib.error

from kupfer.objects import TextSource, TextLeaf, FileLeaf, UrlLeaf
from kupfer.obj.objects import OpenUrl
from kupfer import utils

__kupfer_name__ = "Free-text Queries"
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", "URLTextSource",)
__kupfer_actions__ = ("OpenTextUrl", )
__description__ = "Basic support for free-text queries"
__version__ = "2009-12-16"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class BasicTextSource (TextSource):
    """The most basic TextSource yields one TextLeaf"""
    def __init__(self):
        TextSource.__init__(self, name=_("Text"))

    def get_text_items(self, text):
        if not text:
            return
        yield TextLeaf(text)
    def provides(self):
        yield TextLeaf


class PathTextSource (TextSource):
    """Return existing full paths if typed"""
    def __init__(self):
        TextSource.__init__(self, name="Filesystem Text Matches")

    def get_rank(self):
        return 80
    def get_text_items(self, text):
        # Find directories or files
        if text.startswith("file:///"):
            leaf = FileLeaf.from_uri(text)
            if leaf and leaf.is_valid():
                yield leaf
        else:
            prefix = os.path.expanduser("~/")
            ufilepath = text if os.path.isabs(text) else os.path.join(prefix, text)
            filepath = os.path.normpath(ufilepath)
            if os.access(filepath, os.R_OK):
                yield FileLeaf(filepath)
    def provides(self):
        yield FileLeaf

def is_url(text):
    """If @text is an URL, return a cleaned-up URL, else return None"""
    text = text.strip()
    components = list(urllib.parse.urlparse(text))
    domain = "".join(components[1:])
    dotparts = domain.rsplit(".")

    # 1. Domain name part is one word (without spaces)
    # 2. Urlparse parses a scheme (http://), else we apply heuristics
    if len(domain.split()) == 1 and (components[0] or ("." in domain and
        len(dotparts) >= 2 and len(dotparts[-1]) >= 2 and
        any(char.isalpha() for char in domain) and
        all(part[:1].isalnum() for part in dotparts))):
        if not components[0]:
            url = "http://" + "".join(components[1:])
        else:
            url = text
        name = ("".join(components[1:3])).strip("/")
        if name:
            return url

def try_unquote_url(url):
    """Try to turn an URL-escaped string into a Unicode string

    Where we assume UTF-8 encoding; and return the original url if
    any step fails.
    """
    return urllib.parse.unquote(url)

class OpenTextUrl (OpenUrl):
    rank_adjust = 1

    def activate(self, leaf):
        url = is_url(leaf.object)
        utils.show_url(url)

    def item_types(self):
        yield TextLeaf
    def valid_for_item(self, leaf):
        return is_url(leaf.object)

class URLTextSource (TextSource):
    """detect URLs and webpages"""
    def __init__(self):
        TextSource.__init__(self, name="URL Text Matches")

    def get_rank(self):
        return 75
    def get_text_items(self, text):
        # Only detect "perfect" URLs
        text = text.strip()
        components = list(urllib.parse.urlparse(text))
        domain = "".join(components[1:])

        # If urlparse parses a scheme (http://), it's an URL
        if len(domain.split()) <= 1 and components[0]:
            url = text
            name = ("".join(components[1:3])).strip("/")
            name = try_unquote_url(name) or url
            yield UrlLeaf(url, name=name)

    def provides(self):
        yield UrlLeaf
