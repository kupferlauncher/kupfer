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

import gobject

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf, SourceLeaf, TextSource, FileLeaf
from kupfer.obj.objects import ConstructFileLeaf
from kupfer import utils, pretty
from kupfer import plugin_support



plugin_support.check_dbus_connection()

SERVICE_NAME = "org.freedesktop.Tracker"
SEARCH_OBJECT_PATH = "/org/freedesktop/Tracker/Search"
SEARCH_INTERFACE = "org.freedesktop.Tracker.Search"

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

class TrackerQuerySource (Source):
	def __init__(self, query):
		Source.__init__(self, name=_('Results for "%s"') % query)
		self.query = query
		self.max_items = 50

	def get_items(self):
		try:
			import dbus
		except ImportError:
			pretty.print_info(__name__, "Dbus not available!")
			return
		bus = dbus.SessionBus()
		try:
			tobj = bus.get_object(SERVICE_NAME, SEARCH_OBJECT_PATH)
			searchobj = dbus.Interface(tobj, SEARCH_INTERFACE)
		except dbus.DBusException, exc:
			pretty.print_error(__name__, exc)
			pretty.print_error(__name__, "Could not connect to Tracker")
			return

		# Text interface
		# (i) live_query_id, (s) service, (s) search_text,
		# (i) offset, (i) max_hits
		# Returns array of strings for results
		try:
			file_hits = searchobj.Text(1, "Files", self.query, 0, self.max_items)
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
def get_tracker_tags(for_file=None):
	from os import popen
	if not for_file:
		output = popen("tracker-tag --list").readlines()
		for tagline in output[1:]:
			tag, count = tagline.rsplit(",", 1)
			tag = tag.strip()
			yield tag
	else:
		output = popen("tracker-tag --list '%s'" % for_file).readlines()
		for tagline in output[1:]:
			fil, tagstr = tagline.rsplit(": ", 1)
			tags = tagstr.strip().split("|")
			for t in filter(None, tags):
				yield t

def get_tracker_tag_items(tag):
	from os import popen
	output = popen("tracker-tag -s '%s'" % tag).readlines()
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

