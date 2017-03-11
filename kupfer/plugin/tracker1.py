"""
Tracker plugins are versioned by the D-Bus API version
This is version works with Tracker1.
"""
__kupfer_name__ = _("Tracker")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("TrackerFulltext", )
__kupfer_contents__ = ("TrackerQuerySource", )
__kupfer_actions__ = (
        "TrackerSearch",
        "TrackerSearchHere",
    )
__description__ = _("Tracker desktop search integration")
__version__ = "2017.2"
__author__ = "US"

import os
from xml.etree.cElementTree import ElementTree

from gi.repository import Gio 
import dbus

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf, FileLeaf, TextSource, OperationError
from kupfer import utils, pretty
from kupfer import plugin_support


plugin_support.check_dbus_connection()

SERVICE_NAME = "org.freedesktop.Tracker"
SEARCH_OBJECT_PATH = "/org/freedesktop/Tracker/Search"
SEARCH_INTERFACE = "org.freedesktop.Tracker.Search"

SERVICE1_NAME = "org.freedesktop.Tracker1"
SEARCH_OBJECT1_PATH = "/org/freedesktop/Tracker1/Resources"
SEARCH1_INTERFACE = "org.freedesktop.Tracker1.Resources"

TRACKER_GUI_SEARCH = "tracker-needle"

class TrackerSearch (Action):
    def __init__(self):
        Action.__init__(self, _("Search in Tracker"))

    def activate(self, leaf):
        try:
            utils.spawn_async_raise([TRACKER_GUI_SEARCH, leaf.object])
        except utils.SpawnError as exc:
            raise OperationError(exc)
    def get_description(self):
        return _("Open Tracker Search Tool and search for this term")
    def get_icon_name(self):
        return "system-search"
    def item_types(self):
        yield TextLeaf

class TrackerSearchHere(Action):
    action_accelerator = "t"
    def __init__(self):
        super().__init__(_("Get Tracker Results..."))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        query = leaf.object

        def error(exc):
            ctx.register_late_error(exc)

        def reply(results):
            ret = []
            new_file = Gio.File.new_for_uri
            for result in results:
                try:
                    ret.append(FileLeaf(new_file(result[0]).get_path()))
                except Exception: # This very vague exception is from getpath
                    continue
            ctx.register_late_result(TrackerQuerySource(query, search_results=ret))

        for _ignore in get_tracker_filequery(query, max_items=500,
                operation_err=True,
                reply_handler=reply, error_handler=error):
            pass

    def get_description(self):
        return _("Show Tracker results for query")
    def get_icon_name(self):
        return "tracker"
    def item_types(self):
        yield TextLeaf

def sparql_escape(ustr):
    """Escape unicode string @ustr for insertion into a SPARQL query

    Implemented to behave like tracker_sparql_escape in libtracker-client
    """
    sparql_escape_table = {
        ord('\t'): r'\t',
        ord('\n'): r'\n',
        ord('\r'): r'\r',
        ord('\b'): r'\b',
        ord('\f'): r'\f',
        ord('"') : r'\"',
        ord('\\'): '\\\\',
        # Extra rule: Can't have ?
        ord("?") : "",
    }
    return ustr.translate(sparql_escape_table)

ORDER_BY = {
    "rank": "ORDER BY DESC (fts:rank(?s))",
    "recent": "ORDER BY DESC (nfo:fileLastModified(?s))",
}
def get_file_results_sparql(searchobj, query, max_items=50, order_by="rank",
                            location=None, **kwargs):
    clean_query = sparql_escape(query)

    if location:
        location_filter = \
        'FILTER(tracker:uri-is-descendant ("%s", nie:url (?s)))' % sparql_escape(location)
    else:
        location_filter = ""

    sql = ("""SELECT tracker:coalesce (nie:url (?s), ?s)
              WHERE {
                ?s fts:match "%(query)s" .  ?s tracker:available true .
                %(location_filter)s
              }
              %(order_by)s
              OFFSET 0 LIMIT %(limit)d""" % dict(
              query=clean_query,
              location_filter=location_filter,
              order_by=ORDER_BY[order_by],
              limit=int(max_items))
              )

    pretty.print_debug(__name__, sql)
    results = searchobj.SparqlQuery(sql, **kwargs)
    if results is None:
        return

    new_file = Gio.File.new_for_uri
    for result in results:
        try:
            yield FileLeaf(new_file(result[0]).get_path())
        except Exception: # This very vague exception is from getpath
            continue

use_version = "0.8"
versions = {
    "0.8": (SERVICE1_NAME, SEARCH_OBJECT1_PATH, SEARCH1_INTERFACE),
}

version_query = {
    "0.8": get_file_results_sparql,
}


def get_searchobject(sname, opath, sinface, operation_err=False):
    bus = dbus.SessionBus()
    searchobj = None
    try:
        tobj = bus.get_object(sname, opath)
        searchobj = dbus.Interface(tobj, sinface)
    except dbus.DBusException as exc:
        if operation_err:
            raise OperationError(exc)
        pretty.print_debug(__name__, exc)
    return searchobj

def get_tracker_filequery(query, operation_err=False, **kwargs):
    searchobj = get_searchobject(*versions[use_version],
                                 operation_err=operation_err)
    if searchobj is None:
        pretty.print_error(__name__, "Could not connect to Tracker")
        return ()

    queryfunc = version_query[use_version]
    return queryfunc(searchobj, query, **kwargs)

class TrackerQuerySource (Source):
    def __init__(self, query, search_results=None, **search_args):
        Source.__init__(self, name=_('Tracker Search for "%s"') % query)
        self.query = query
        self.search_args = search_args
        self.search_results = None

    def repr_key(self):
        return self.query

    def get_items(self):
        if self.search_results:
            return self.search_results
        else:
            return get_tracker_filequery(self.query, **self.search_args)

    def provides(self):
        yield FileLeaf

    def get_description(self):
        return _('Results for "%s"') % self.query
    def get_icon_name(self):
        return "tracker"

    @classmethod
    def decorates_type(cls):
        return FileLeaf

    @classmethod
    def decorate_item(cls, leaf):
        # FIXME: Very simplified .savedSearch parsing, so far we only support
        # the query, without additional filtering. The simplest form of
        # .savedSearch file is saved by nautilus as following:
        # <query version="1.0">
        #   <text>QUERY GOES HERE</text>
        # </query>

        if not leaf.object.endswith(".savedSearch"):
            return None
        try:
            et = ElementTree(file=leaf.object)
            query = et.getroot().find("text").text
            if not query:
                return None
            location_tag = et.getroot().find("location")
            location = location_tag.text if location_tag is not None else None
            return cls(query, location=location_uri(location))
        except Exception:
            pretty.print_exc(__name__)
            return None

def location_uri(location):
    if location is None:
        return None
    if not os.path.isabs(location):
        location = os.path.expanduser("~/" + location)
    return Gio.File.new_for_path(location).get_uri()

# FIXME: Port tracker tag sources and actions
# to the new, much more powerful sparql + dbus API
# (using tracker-tag as in 0.6 is a plain hack and a dead end)

class TrackerFulltext (TextSource):
    def __init__(self):
        TextSource.__init__(self, name=_('Tracker Full Text Search'))

    def get_description(self):
        return _("Use '?' prefix to get full text results")

    def get_text_items(self, text):
        if text.startswith("?"):
            rank = "rank"
            if text.startswith("?~"):
                rank = "recent"
            query = text.lstrip("? ~")
            if len(query) > 2 and not has_parsing_error(query):
                yield from TrackerQuerySource(query, order_by=rank, max_items=50).get_items()

    def provides(self):
        yield FileLeaf

    def get_rank(self):
        return 80


def has_parsing_error(query):
    "Check common parsing errors"
    words = query.split()
    # Unfinshed "" and OR, AND without following won't parse
    if words and words[-1] in ("OR", "AND"):
        return True
    if query.count('"') % 2 != 0:
        return True
    return False
