import wnck
import gtk
import gobject
from time import time

from kupfer import pretty

kupfer_env = "KUPFER_APP_ID"

def read_environ(pid, envcache=None):
	"""Read the environment for application with @pid
	and return as a dictionary. Only works for the user's
	own processes, of course
	"""
	if envcache and pid in envcache:
		return envcache[pid]
	try:
		f = open("/proc/%d/environ" % int(pid), "r")
	except IOError:
		return None
	else:
		env = f.read()
	environ = {}
	for line in env.split("\x00"):
		vals = line.split("=", 1)
		if len(vals) == 2:
			environ[vals[0]] = vals[1]
		else:
			continue
	if envcache: envcache[pid] = env
	return environ

class ApplicationsMatcherService (pretty.OutputMixin):
	"""Handle launching applications and see if they still run.
	This is a learning service, since we have no first-class application
	object on the Linux desktop
	"""
	def __init__(self):
		self.register = {}
		screen = wnck.screen_get_default()
		screen.get_windows_stacked()
	def _store(self, app_id, application):
		self.register[app_id] = application.get_name()
		self.output_debug("storing", app_id, "as", application.get_name())
	def _has_match(self, app_id):
		return app_id in self.register
	def _is_match(self, app_id, application):
		if not self._has_match(app_id):
			return False
		return self.register[app_id] == application.get_name()

	def launched_application(self, app_id):
		timeout = time() + 10
		envcache = {}
		gobject.timeout_add_seconds(2, self._find_application, app_id, timeout, envcache)

	def _find_application(self, app_id, timeout, envcache=None):
		screen = wnck.screen_get_default()
		for w in screen.get_windows_stacked():
			app = w.get_application()
			pid = app.get_pid()
			if not pid:
				print app.get_name(), app.get_startup_id(), app.get_icon_name(), app.get_xid()
				pid = w.get_pid()
				print "Found ", pid, "instead"
			self.output_debug("App %s has pid %d" %( app.get_name(), pid))
			env = read_environ(pid, envcache=envcache)
			if env and kupfer_env in env:
				if env[kupfer_env] == app_id:
					self._store(app_id, app)
					return False
		if time() > timeout:
			return False
		return True

	def application_is_running(self, app_id):
		if not self._has_match(app_id):
			return False
		screen = wnck.screen_get_default()
		for w in screen.get_windows_stacked():
			app = w.get_application()
			if self._is_match(app_id, app):
				self.output_debug(app_id, "is running")
				return True
		return False

	def application_to_front(self, app_id):
		if not self._has_match(app_id):
			return False
		screen = wnck.screen_get_default()
		for w in screen.get_windows_stacked():
			app = w.get_application()
			if self._is_match(app_id, app):
				self.output_debug(app_id, "is running")
				break
		# if break not reached
		else:
			return False

		# for now, just take any window
		evttime = gtk.get_current_event_time()
		wspc = w.get_workspace()
		wspc.activate(evttime)
		w.activate(evttime)


_appl_match_service = None
def GetApplicationsMatcherService():
	"""Get the (singleton) ApplicationsMatcherService"""
	global _appl_match_service
	if not _appl_match_service:
		_appl_match_service = ApplicationsMatcherService()
	return _appl_match_service

