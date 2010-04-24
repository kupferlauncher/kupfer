__kupfer_name__ = _("Tracker")
__kupfer_sources__ = ("TrackerTagsSource", )
__kupfer_text_sources__ = ()
__kupfer_contents__ = ("TrackerQuerySource", )
__kupfer_actions__ = (
		"TrackerSearch",
		"TrackerSearchHere",
		"TrackerAddTag",
		"TrackerRemoveTag",
	)
__description__ = _("Tracker desktop search integration")
__version__ = "2010-01-03"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
from xml.etree.cElementTree import ElementTree

import dbus
import gio
import gobject

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf, SourceLeaf, TextSource, FileLeaf
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

class TrackerSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Tracker"))

	def activate(self, leaf):
		utils.launch_commandline("tracker-search-tool %s" % leaf.object)
	def get_description(self):
		return _("Open Tracker Search Tool and search for this term")
	def get_icon_name(self):
		return "search"
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

def is_ok_char(c):
	return c.isalnum() or c == " "

def get_file_results_sparql(searchobj, query, max_items):
	# We don't have any real escape function for queries
	# so we instead strip everything not alphanumeric
	clean_query = u"".join([c for c in query if is_ok_char(c)])
	sql = u"""SELECT tracker:coalesce (nie:url (?s), ?s)
	          WHERE {  ?s fts:match "%s*" .  ?s tracker:available true . }
			  ORDER BY tracker:weight(?s)
			  OFFSET 0 LIMIT %d""" % (clean_query, int(max_items))

	pretty.print_debug(__name__, "Searching for %s (%s)",
			repr(clean_query), repr(query))
	pretty.print_debug(__name__, sql)
	results = searchobj.SparqlQuery(sql)

	gio_File = gio.File
	for result in results:
		yield FileLeaf(gio_File(result[0]).get_path())

def get_file_results_old(searchobj, query, max_items):
	try:
		file_hits = searchobj.Text(1, "Files", query, 0, max_items)
	except dbus.DBusException, exc:
		pretty.print_error(__name__, exc)
		return

	for filestr in file_hits:
		# A bit of encoding carousel
		# dbus strings are subclasses of unicode
		# but FileLeaf expects a filesystem encoded object
		bytes = filestr.decode("UTF-8", "replace")
		filename = gobject.filename_from_utf8(bytes)
		yield ConstructFileLeaf(filename)

use_version = None
versions = {
	"0.8": (SERVICE1_NAME, SEARCH_OBJECT1_PATH, SEARCH1_INTERFACE),
	"0.6": (SERVICE_NAME, SEARCH_OBJECT_PATH, SEARCH_INTERFACE),
}

version_query = {
	"0.8": get_file_results_sparql,
	"0.6": get_file_results_old,
}


def get_searchobject(sname, opath, sinface):
	bus = dbus.SessionBus()
	searchobj = None
	try:
		tobj = bus.get_object(sname, opath)
		searchobj = dbus.Interface(tobj, sinface)
	except dbus.DBusException, exc:
		pretty.print_debug(__name__, exc)
	return searchobj

def get_tracker_filequery(query, max_items):
	searchobj = None
	global use_version
	if use_version is None:
		for version, (sname, opath, sinface) in versions.items():
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
	def __init__(self, query):
		Source.__init__(self, name=_('Results for "%s"') % query)
		self.query = query
		self.max_items = 50

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
			return cls(query)
		except Exception:
			return None

# FIXME: Use dbus for this communication
def cmd_output_lines(cmd):
	return kupferstring.fromlocale(os.popen(cmd).read()).splitlines()

def get_tracker_tags(for_file=None):
	if not for_file:
		for tagline in cmd_output_lines("tracker-tag --list")[1:]:
			tag, count = tagline.rsplit(",", 1)
			tag = tag.strip()
			yield tag
	else:
		output = cmd_output_lines("tracker-tag --list '%s'" % for_file)
		for tagline in output[1:]:
			fil, tagstr = tagline.rsplit(": ", 1)
			tags = tagstr.strip().split("|")
			for t in filter(None, tags):
				yield t

def get_tracker_tag_items(tag):
	output = cmd_output_lines("tracker-tag -s '%s'" % tag)
	for tagline in output[1:]:
		yield tagline.strip()

class TrackerFileTagsSource (Source):
	"""Tracker tags for a specific file"""
	def __init__(self, fil=None):
		""" All tags for file @fil or all tags known if None"""
		Source.__init__(self, _("Tracker tags"))
		self.for_file = fil
	def get_items(self):
		for tag in get_tracker_tags(self.for_file):
			yield TrackerTag(tag)
	def get_description(self):
		return _("Tracker tags")
	def get_icon_name(self):
		return "tracker"
	def provides(self):
		yield TrackerTag

class TrackerTagsSource (Source):
	"""Browse items tagged in Tracker"""
	def __init__(self):
		Source.__init__(self, _("Tracker Tags"))
	def get_items(self):
		for tag in get_tracker_tags():
			src = TrackerTagObjectsSource(tag)
			yield SourceLeaf(src)
	def get_description(self):
		return _("Browse Tracker's tags")
	def get_icon_name(self):
		return "tracker"
	def provides(self):
		yield TrackerTag

class TrackerTag (Leaf):
	""" Represents a tag without actions """
	def __init__(self, tag):
		Leaf.__init__(self, tag, tag)
	def get_description(self):
		return _("Tag %s") % self.object
	def get_icon_name(self):
		return "user-bookmarks"

class TrackerTagObjectsSource (Source):
	"""This source shows all items of one tracker tag"""
	def __init__(self, tag):
		Source.__init__(self, _("Tag %s") % tag)
		self.tag = tag
	def is_dynamic(self):
		return True
	def get_items(self):
		return (ConstructFileLeaf(f) for f in get_tracker_tag_items(self.tag))
	def get_description(self):
		return _("Objects tagged %s with Tracker") % self.tag
	def get_icon_name(self):
		return "user-bookmarks"

class TrackerAddTag (Action):
	""" Add tracker tags.

	FIXME: Only tracker-indexed directories can be tagged
	I don't know how to check that effectively. 
	So we allow everything here
	"""
	def __init__(self):
		Action.__init__(self, _("Add Tag..."))
	def activate(self, leaf, obj):
		lpath = leaf.object
		tag = obj.object
		utils.launch_commandline("tracker-tag --add='%s' '%s'" % (obj, lpath))

	def requires_object(self):
		return True

	def item_types(self):
		yield FileLeaf
	def object_types(self):
		yield TextLeaf
		yield TrackerTag

	def object_source(self, for_item=None):
		# FIXME: We list all tags. We don't want to list tags it already has
		return TrackerFileTagsSource()

	def valid_object(self, obj, for_item):
		if isinstance(obj, TextLeaf):
			# FIXME: Do tag syntax checking here
			return (u" " not in obj.object)
		return True

	def get_description(self):
		return _("Add tracker tag to file")
	def get_icon_name(self):
		return "gtk-add"

class TrackerRemoveTag (Action):
	def __init__(self):
		Action.__init__(self, _("Remove Tag..."))
	def activate(self, leaf, obj):
		lpath = leaf.object
		tag = obj.object
		utils.launch_commandline("tracker-tag --remove='%s' '%s'" % (obj, lpath))

	def requires_object(self):
		return True

	def item_types(self):
		yield FileLeaf
	def object_types(self):
		yield TrackerTag

	def object_source(self, for_item):
		path = for_item.object
		return TrackerFileTagsSource(path)

	def get_description(self):
		return _("Remove tracker tag from file")
	def get_icon_name(self):
		return "gtk-remove"

