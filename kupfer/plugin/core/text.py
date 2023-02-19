from __future__ import annotations

import typing as ty

import os
import urllib.error
import urllib.parse
import urllib.request
import socket

from kupfer import utils
from kupfer.support import pretty
from kupfer.support.validators import is_url
from kupfer.obj import FileLeaf, OpenUrl, TextLeaf, TextSource, UrlLeaf

__kupfer_name__ = "Free-text Queries"
__kupfer_sources__ = ()
__kupfer_text_sources__ = (
    "BasicTextSource",
    "PathTextSource",
    "URLTextSource",
)
__kupfer_actions__ = ("OpenTextUrl",)
__description__ = "Basic support for free-text queries"
__version__ = "2021.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


if ty.TYPE_CHECKING:
    _ = str


class BasicTextSource(TextSource):
    """The most basic TextSource yields one TextLeaf"""

    def __init__(self):
        TextSource.__init__(self, name=_("Text"))

    def get_text_items(self, text):
        if text:
            yield TextLeaf(text)

    def provides(self):
        yield TextLeaf


class PathTextSource(TextSource, pretty.OutputMixin):
    """Return existing full paths if typed"""

    def __init__(self):
        TextSource.__init__(self, name="Filesystem Text Matches")
        self._hostname: str | None = None

    def get_rank(self):
        return 80

    def _get_hostname(self) -> str:
        if self._hostname is None:
            try:
                self._hostname = socket.gethostname()
            except Exception:
                self._hostname = ""
                self.output_exc()

        assert self._hostname
        return self._hostname

    def _is_local_file_url(self, url):
        # Recognize file:/// or file://localhost/ or file://<local_hostname>/ URLs
        if url.startswith("file:"):
            hostname = self._get_hostname()
            for prefix in (
                "file:///",
                "file://localhost/",
                f"file://{hostname}/",
            ):
                if url.startswith(prefix):
                    return True

        return False

    def get_text_items(self, text):
        # Find directories or files
        if self._is_local_file_url(text):
            leaf = FileLeaf.from_uri(text)
            if leaf and leaf.is_valid():
                yield leaf

        else:
            prefix = os.path.expanduser("~/")
            ufilepath = (
                text if os.path.isabs(text) else os.path.join(prefix, text)
            )
            filepath = os.path.normpath(ufilepath)
            if os.access(filepath, os.R_OK):
                yield FileLeaf(filepath)

    def provides(self):
        yield FileLeaf


def try_unquote_url(url: str) -> str:
    """Try to turn an URL-escaped string into a Unicode string

    Where we assume UTF-8 encoding; and return the original url if
    any step fails.
    """
    return urllib.parse.unquote(url)


class OpenTextUrl(OpenUrl):
    rank_adjust = 1

    def activate(self, leaf, iobj=None, ctx=None):
        if url := is_url(leaf.object):
            utils.show_url(url)

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        return is_url(leaf.object)


class URLTextSource(TextSource):
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
