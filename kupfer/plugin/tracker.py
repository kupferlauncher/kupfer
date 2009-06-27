import gobject

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf, ActionDecorator, ConstructFileLeaf
from kupfer import utils


__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_action_decorator__ = ("TrackerDecorator", )
__description__ = _("Tracker desktop search integration")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class TrackerDecorator (ActionDecorator):
	"""Base class for an object assigning more actions to Leaves"""
	def applies_to(self):
		yield TextLeaf
	def get_actions(self, leaf=None):
		return (TrackerSearch(), TrackerSearchHere())

class TrackerSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Tracker"))

	def activate(self, leaf):
		utils.launch_commandline("tracker-search-tool %s" % leaf.object)
	def get_description(self):
		return _("Open tracker to search for this term")
	def get_icon_name(self):
		return "search"

class TrackerSearchHere (Action):
	def __init__(self):
		Action.__init__(self, _("Query Tracker..."))

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
			print "Dbus not available!"
			return
		bus = dbus.SessionBus()
		try:
			searchobj = bus.get_object("org.freedesktop.Tracker",
					"/org/freedesktop/Tracker/Search")
		except dbus.DBusException:
			print "Tracker not found on bus"
			return

		# Text interface
		# (i) live_query_id, (s) service, (s) search_text,
		# (i) offset, (i) max_hits
		# Returns array of strings for results
		try:
			file_hits = searchobj.Text(1, "Files", self.query, 0, self.max_items)
		except dbus.DBusException:
			print "Tracker not found on bus"
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

