from __future__ import annotations

__kupfer_name__ = "Free-text Queries"
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", "URLTextSource")
__kupfer_actions__ = ("OpenTextUrl",)
__description__ = "Basic support for free-text queries"
__version__ = "2021.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import typing as ty
import urllib.error
import urllib.parse
import urllib.request
from contextlib import suppress
from pathlib import Path

from kupfer import launch
from kupfer.obj import FileLeaf, Leaf, OpenUrl, TextLeaf, TextSource, UrlLeaf
from kupfer.support import pretty, system
from kupfer.support.validators import is_url

if ty.TYPE_CHECKING:
    from gettext import gettext as _


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

    def get_rank(self):
        return 80

    def _is_local_file_url(self, url: str) -> bool:
        # Recognize file:/// or file://localhost/ or file://<local_hostname>/ URLs
        hostname = system.get_hostname()
        return url.startswith(
            ("file:///", "file://localhost/", f"file://{hostname}/")
        )

    def get_text_items(self, text: str) -> ty.Iterator[Leaf]:
        # Find directories or files
        if self._is_local_file_url(text):
            leaf = FileLeaf.from_uri(text)
            if leaf and leaf.is_valid():
                yield leaf

            return

        urlpath = Path(text)
        if not urlpath.is_absolute():
            urlpath = Path(system.get_homedir()).joinpath(urlpath)

        with suppress(OSError):
            filepath = urlpath.resolve(strict=True)
            if os.access(filepath, os.R_OK):
                yield FileLeaf(filepath)

    def provides(self):
        yield FileLeaf


class OpenTextUrl(OpenUrl):
    rank_adjust = 1

    def activate(self, leaf, iobj=None, ctx=None):
        if url := self._get_leaf_valid_url(leaf):
            launch.show_url(url)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf: Leaf) -> bool:
        return bool(self._get_leaf_valid_url(leaf))

    def _get_leaf_valid_url(self, leaf: Leaf) -> str | None:
        if isinstance(leaf, TextLeaf):
            if url := is_url(leaf.object):
                return url

        with suppress(AttributeError):
            if trepr := leaf.get_text_representation():  # type: ignore
                if url := is_url(trepr):
                    return url

        with suppress(AttributeError, NotImplementedError):
            for url in leaf.get_urilist_representation() or []:  # type: ignore
                if url and (url := is_url(url)):
                    return url

        return None


class URLTextSource(TextSource):
    """detect URLs and webpages"""

    def __init__(self):
        TextSource.__init__(self, name="URL Text Matches")

    def get_rank(self):
        return 75

    def get_text_items(self, text: str) -> ty.Iterator[Leaf]:
        # Only detect "perfect" URLs
        text = text.strip()
        if not text:
            return

        components = urllib.parse.urlparse(text)

        # scheme and netloc are required
        if not components.scheme or not components.netloc:
            return

        # check for any whitespaces; quick and dirty
        if len(text.split(None, 1)) != 1:
            return

        name = f"{components.netloc}{components.path}".strip("/")
        # Try to turn an URL-escaped string into a Unicode string
        name = urllib.parse.unquote(name) or text
        yield UrlLeaf(text, name=name)

    def provides(self):
        yield UrlLeaf
