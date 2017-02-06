"""
Tracker plugins are versioned by the D-Bus API version
This is version works with tracker 0.8.x and 0.10.x, where the API is called
Tracker1

Tracker 0.10 has exactly the same Resources.SparqlQuery API, but according to
its developers it does not have the same class signal api but that does not
impact this plugin.
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
__version__ = "2017.1"
__author__ = "US"

from xml.etree.cElementTree import ElementTree

from gi.repository import Gio, GLib
import dbus

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf, FileLeaf, TextSource, SourceLeaf
from kupfer.obj.objects import ConstructFileLeaf
from kupfer import utils, pretty
from kupfer import kupferstring
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
        utils.spawn_async([TRACKER_GUI_SEARCH, leaf.object])
    def get_description(self):
        return _("Open Tracker Search Tool and search for this term")
    def get_icon_name(self):
        return "system-search"
    def item_types(self):
        yield TextLeaf

class TrackerSearchHere (Action):
    def __init__(self):
        Action.__init__(self, _("Get Tracker Results..."))

    def is_factory(self):
        return True

    def activate(self, leaf):
        return TrackerQuerySource(leaf.object)

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

def get_file_results_sparql(searchobj, query, max_items):
    clean_query = sparql_escape(query)
    sql = """SELECT tracker:coalesce (nie:url (?s), ?s)
              WHERE {  ?s fts:match "%s" .  ?s tracker:available true . }
              ORDER BY DESC (fts:rank(?s))
              OFFSET 0 LIMIT %d""" % (clean_query, int(max_items))

    results = searchobj.SparqlQuery(sql)

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


def get_searchobject(sname, opath, sinface):
    bus = dbus.SessionBus()
    searchobj = None
    try:
        tobj = bus.get_object(sname, opath)
        searchobj = dbus.Interface(tobj, sinface)
    except dbus.DBusException as exc:
        pretty.print_debug(__name__, exc)
    return searchobj

def get_tracker_filequery(query, max_items):
    searchobj = None
    global use_version
    if use_version is None:
        for version, (sname, opath, sinface) in list(versions.items()):
            pretty.print_debug(__name__, "Trying", sname, version)
            searchobj = get_searchobject(sname, opath, sinface)
            if searchobj is not None:
                use_version = version
                break
    else:
        searchobj = get_searchobject(*versions[use_version])
    if searchobj is None:
        use_version = None
        pretty.print_error(__name__, "Could not connect to Tracker")
        return ()

    queryfunc = version_query[use_version]
    return queryfunc(searchobj, query, max_items)

class TrackerQuerySource (Source):
    def __init__(self, query, max_items=50):
        Source.__init__(self, name=_('Tracker Search for "%s"') % query)
        self.query = query
        self.max_items = max_items

    def repr_key(self):
        return self.query

    def get_items(self):
        return get_tracker_filequery(self.query, self.max_items)

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
            us_query = kupferstring.tounicode(query)
            return cls(us_query)
        except Exception:
            return None


# FIXME: Port tracker tag sources and actions
# to the new, much more powerful sparql + dbus API
# (using tracker-tag as in 0.6 is a plain hack and a dead end)

class TrackerFulltext (TextSource):
    def __init__(self):
        TextSource.__init__(self, name=_('Tracker Full Text Search'))
        self.max_items = 150

    def get_description(self):
        return _("Use '?' prefix to get full text results")

    def get_text_items(self, text):
        if text.startswith("?"):
            query = text.lstrip("? ")
            if len(query) > 2 and not has_parsing_error(query):
                yield from TrackerQuerySource(query, self.max_items).get_items()

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
