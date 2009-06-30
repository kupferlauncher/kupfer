import gobject

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextSource, ConstructFileLeaf
from kupfer import utils, pretty


__kupfer_text_sources__ = ("TrackerLiveSearchSource", )
__description__ = _("Live Tracker search")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class TrackerLiveSearchSource (TextSource):
	def __init__(self):
		TextSource.__init__(self, name=_("Live Tracker search"))
		self.max_items = 20
		self.searchobj = None
		self.dbus = None

	def _find_tracker(self):
		try:
			import dbus
		except ImportError:
			pretty.print_info(__name__, "Dbus not available!")
			return
		self.dbus = dbus
		bus = dbus.SessionBus()
		try:
			self.searchobj = bus.get_object("org.freedesktop.Tracker",
					"/org/freedesktop/Tracker/Search")
		except dbus.DBusException:
			pretty.print_info(__name__, "Tracker not found on bus")

	def get_rank(self):
		return 70
	def get_items(self, query):
		if not self.searchobj:
			self._find_tracker()
		if not self.searchobj:
			return

		# Text interface
		# (i) live_query_id, (s) service, (s) search_text,
		# (i) offset, (i) max_hits
		# Returns array of strings for results
		try:
			file_hits = self.searchobj.Text(1, "Files", query, 0, self.max_items)
		except self.dbus.DBusException:
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

