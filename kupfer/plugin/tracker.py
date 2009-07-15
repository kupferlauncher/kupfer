import gobject

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import (TextLeaf, ActionDecorator, ConstructFileLeaf,
		SourceLeaf, TextSource, FileLeaf)
from kupfer import utils, pretty
from kupfer.plugin import text


__kupfer_name__ = _("Tracker")
__kupfer_sources__ = ("TrackerTagsSource", )
__kupfer_text_sources__ = ()
__kupfer_action_decorator__ = ("TrackerDecorator", "TrackerTagDecorator")
__description__ = _("Tracker desktop search integration")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class TrackerDecorator (ActionDecorator):
	def applies_to(self):
		yield TextLeaf
	def get_actions(self, leaf=None):
		return (TrackerSearch(), TrackerSearchHere())

class TrackerTagDecorator (ActionDecorator):
	def applies_to(self):
		yield FileLeaf
	def get_actions(self, leaf=None):
		yield TrackerAddTag()

class TrackerSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Tracker"))

	def activate(self, leaf):
		utils.launch_commandline("tracker-search-tool %s" % leaf.object)
	def get_description(self):
		return _("Open Tracker Search Tool and search for this term")
	def get_icon_name(self):
		return "search"

class TrackerSearchHere (Action):
	def __init__(self):
		Action.__init__(self, _("Get Tracker results..."))

	def is_factory(self):
		return True

	def activate(self, leaf):
		return TrackerQuerySource(leaf.object)

	def get_description(self):
		return _("Show Tracker results for query")
	def get_icon_name(self):
		return "tracker"

class TrackerQuerySource (Source):
	def __init__(self, query):
		Source.__init__(self, name=_('Tracker query'))
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
			searchobj = bus.get_object("org.freedesktop.Tracker",
					"/org/freedesktop/Tracker/Search")
		except dbus.DBusException:
			pretty.print_info(__name__, "Tracker not found on bus")
			return

		# Text interface
		# (i) live_query_id, (s) service, (s) search_text,
		# (i) offset, (i) max_hits
		# Returns array of strings for results
		try:
			file_hits = searchobj.Text(1, "Files", self.query, 0, self.max_items)
		except dbus.DBusException:
			pretty.print_info(__name__, "Tracker not found on bus")
			return

		for filestr in file_hits:
			# A bit of encoding carousel
			# dbus strings are subclasses of unicode
			# but FileLeaf expects a filesystem encoded object
			bytes = filestr.decode("UTF-8", "replace")
			filename = gobject.filename_from_utf8(bytes)
			yield ConstructFileLeaf(filename)

	def get_description(self):
		return _('Results for query "%s"') % self.query
	def get_icon_name(self):
		return "tracker"

def get_tracker_tags():
	from os import popen
	output = popen("tracker-tag --list").readlines()
	for tagline in output[1:]:
		tag, count = tagline.rsplit(",", 1)
		tag = tag.strip()
		yield tag

def get_tracker_tag_items(tag):
	from os import popen
	output = popen("tracker-tag -s '%s'" % tag).readlines()
	for tagline in output[1:]:
		yield tagline.strip()

class TrackerTagsSource (Source):
	"""Browse items tagged in Tracker"""
	def __init__(self):
		Source.__init__(self, _("Tracker tags"))
	def get_items(self):
		for tag in get_tracker_tags():
			yield TrackerTag(tag)
	def get_description(self):
		return _("Browse Tracker's tags")
	def get_icon_name(self):
		return "tracker"
	def provides(self):
		yield TrackerTag

class TrackerTag (Leaf):
	def __init__(self, tag):
		Leaf.__init__(self, tag, _("Tag %s") % tag)
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		return TrackerTagObjectsSource(self.object)
	def get_description(self):
		return _("Tracker tag %s") % self.object
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
	def __init__(self):
		Action.__init__(self, _("Add tag..."))
	def activate(self, leaf, obj):
		print "Want to add tag", obj, "to", leaf

	def requires_object(self):
		return True

	def object_types(self):
		yield TextLeaf
		yield TrackerTag

	def object_source(self):
		return TrackerTagsSource()

	def get_icon_name(self):
		return "gtk-add"

