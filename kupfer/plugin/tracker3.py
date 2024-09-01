# pylint: disable=wrong-import-position
"""
Tracker3 plugin using gir1.2-tracker-3.0
"""
from __future__ import annotations

__kupfer_name__ = _("Tracker3")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("Tracker3Fulltext",)
__kupfer_contents__ = ()
__kupfer_actions__ = ("TrackerSearch",)
__description__ = _("Tracker3 search integration")
__version__ = "2023-04-30"
__author__ = "KB"

import typing as ty

import gi

try:
    gi.require_version("Tracker", "3.0")
except ValueError as exc:
    raise ImportError(
        f"{exc}: missing GIRepository Tracker library (gir1.2-tracker-3.0)"
    ) from exc

# pylint: disable=no-name-in-module
from gi.repository import Gio, Tracker

from kupfer.obj import (
    Action,
    FileLeaf,
    Source,
    TextLeaf,
    TextSource,
)

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class TrackerSearch(Action):
    def __init__(self):
        Action.__init__(self, _("Search in Tracker3"))

    def is_factory(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        return QuerySource(leaf.object.strip())

    def get_description(self):
        return _("Search in Tracker3")

    def get_icon_name(self):
        return "system-search"

    def item_types(self):
        yield TextLeaf


_QUERY = """
SELECT ?uri max(?rank) as ?rank WHERE {
    {
        SELECT (?s AS ?uri) (fts:rank(?s) AS ?rank) {
            GRAPH tracker:FileSystem {
                ?s a nfo:FileDataObject ;
                fts:match "%(term)s" ;
                nie:dataSource ?ds .
            }
        }
    }
    UNION {
        SELECT ?uri (fts:rank(?uri) AS ?rank) {
            GRAPH ?g {
                ?s a nie:InformationElement ;
                fts:match "%(term)s" ;
                nie:isStoredAs ?uri .
            }
            GRAPH tracker:FileSystem {
                ?uri nie:dataSource ?ds .
            }
        }
    }
}
GROUP BY ?uri
ORDER BY ?rank
OFFSET 0
LIMIT %(limit)s
"""


def _query(term: str, limit: int) -> ty.Iterator[FileLeaf]:
    miner_fs = Tracker.SparqlConnection.bus_new(
        "org.freedesktop.Tracker3.Miner.Files", None, None
    )
    term = Tracker.sparql_escape_string(term)
    query = _QUERY % {"term": term, "limit": limit}
    if cursor := miner_fs.query(query, None):
        while cursor.next(None):
            if uri := cursor.get_string(0)[0]:
                path = Gio.File.new_for_uri(uri).get_path()
                yield FileLeaf(path)


class QuerySource(Source):
    def __init__(self, query: str, limit: int = 100) -> None:
        Source.__init__(self, name=_('Results for "%s"') % query)
        self.query = query
        self.limit = limit

    def repr_key(self):
        return self.query

    def get_items(self):
        return tuple(_query(self.query, self.limit))


class Tracker3Fulltext(TextSource):
    def __init__(self):
        TextSource.__init__(self, name=_("Tracker3 Full Text Search"))

    def get_description(self):
        return _("Use '?' prefix to get full text results")

    def get_text_items(self, text):
        if text.startswith("?") and (term := text.lstrip("? ")):
            return tuple(_query(term, 25))

        return ()

    def provides(self):
        yield FileLeaf

    def get_rank(self):
        return 80
