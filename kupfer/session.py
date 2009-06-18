"""
session sets up the program as a client to the current
desktop session and enables notifications on session
close, to be able to save state before being killed;

the module API does not depend on the session API used
"""

import gobject
from . import pretty, version

_has_gnomeui = False
try:
	import gnome
	import gnome.ui
except ImportError:
	pass
else:
	_has_gnomeui = True

class SessionClient (gobject.GObject, pretty.OutputMixin):
	"""Session handling controller

	signals:
	save-yourself: Program should save state
	die:           Program should quit
	"""
	__gtype_name__ = "SessionClient"

	def __init__(self):
		"""Set up program as client to current Session"""
		gobject.GObject.__init__(self)
		if _has_gnomeui:
			gnome.program_init(version.PACKAGE_NAME, version.VERSION)
			client = gnome.ui.master_client()
			client.connect("save-yourself", self._session_save)
			client.connect("die", self._session_die)
			self.output_debug("Setting up session connection using GnomeClient")
		self._enabled = _has_gnomeui
		if not self.enabled:
			self.output_info("Not able to connect to current desktop session")
	def _session_save(self, obj, *args):
		self.emit("save-yourself")
	def _session_die(self, obj, *args):
		self.emit("die")
	@property
	def enabled(self):
		"""If a session connection is available"""
		return self._enabled

gobject.signal_new("save-yourself", SessionClient, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("die", SessionClient, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
