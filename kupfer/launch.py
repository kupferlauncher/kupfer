from time import time
import os
import cPickle as pickle

import gtk
import gobject

from kupfer import pretty, config
from kupfer import scheduler
from kupfer.ui import keybindings

try:
	import wnck
except ImportError, e:
	pretty.print_info(__name__, "Disabling launch module:", e)
	wnck = None

kupfer_env = "KUPFER_APP_ID"

default_associations = {
	"evince" : "Document Viewer",
	"file-roller" : "File Roller",
	#"gedit" : "Text Editor",
	"gnome-keyring-manager" : "Keyring Manager",
	"nautilus-browser" : "File Manager",
	"rhythmbox" : "Rhythmbox Music Player",
}


def _read_environ(pid, envcache=None):
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
	if envcache is not None: envcache[pid] = environ
	return environ

def application_id(app_info):
	"""Return an application id (string) for GAppInfo @app_info"""
	app_id = app_info.get_id()
	if not app_id:
		try:
			app_id = app_info.init_path
		except AttributeError:
			app_id = ""
	if app_id.endswith(".desktop"):
		app_id = app_id[:-len(".desktop")]
	return app_id

def _current_event_time():
	return gtk.get_current_event_time() or keybindings.get_current_event_time()

def launch_application(app_info, files=(), uris=(), paths=(), track=True, activate=True):
	"""
	Launch @app_info correctly, using a startup notification

	you may pass in either a list of gio.Files in @files, or 
	a list of @uris or @paths

	if @track, it is a user-level application
	if @activate, activate rather than start a new version
	"""
	assert app_info

	from gtk.gdk import AppLaunchContext
	from gio import File
	from glib import GError

	ctx = AppLaunchContext()
	if paths:
		files = [File(p) for p in paths]

	if wnck:
		# launch on current workspace
		workspace = wnck.screen_get_default().get_active_workspace()
		nbr = workspace.get_number() if workspace else -1
		ctx.set_desktop(nbr)
	ctx.set_timestamp(_current_event_time())

	if track:
		app_id = application_id(app_info)
		os.putenv(kupfer_env, app_id)
	else:
		app_id = ""
	svc = GetApplicationsMatcherService()
	try:
		if activate and svc.application_is_running(app_id):
			svc.application_to_front(app_id)
			return True

		try:
			if uris:
				ret = app_info.launch_uris(uris, ctx)
			else:
				ret = app_info.launch(files, ctx)
			if not ret:
				pretty.print_info(__name__, "Error launching", app_info)
		except GError, e:
			pretty.print_info(__name__, "Error:", e)
			return False
		else:
			if track:
				svc.launched_application(application_id(app_info))
	finally:
		os.unsetenv(kupfer_env)
	return True

def application_is_running(app_info):
	svc = GetApplicationsMatcherService()
	return svc.application_is_running(application_id(app_info))

def application_close_all(app_info):
	svc = GetApplicationsMatcherService()
	return svc.application_close_all(application_id(app_info))

class ApplicationsMatcherService (pretty.OutputMixin):
	"""Handle launching applications and see if they still run.
	This is a learning service, since we have no first-class application
	object on the Linux desktop
	"""
	def __init__(self):
		self.register = {}
		self._get_wnck_screen_windows_stacked()
		scheduler.GetScheduler().connect("finish", self._finish)
		self._load()

	@classmethod
	def _get_wnck_screen_windows_stacked(cls):
		if not wnck:
			return ()
		screen = wnck.screen_get_default()
		return screen.get_windows_stacked()

	def _get_filename(self):
		version = 1
		return os.path.join(config.get_cache_home(),
				"application_identification_v%d.pickle" % version)
	def _load(self):
		reg = self._unpickle_register(self._get_filename())
		self.register = reg if reg else default_associations
		# pretty-print register to debug
		if self.register:
			self.output_debug("Learned the following applications")
			self.output_debug("\n{\n%s\n}" % "\n".join(
				("  %-30s : %s" % (k,v)
					for k,v in self.register.iteritems())
				))
	def _finish(self, sched):
		self._pickle_register(self.register, self._get_filename())
	def _unpickle_register(self, pickle_file):
		try:
			pfile = open(pickle_file, "rb")
		except IOError, e:
			return None
		try:
			source = pickle.loads(pfile.read())
			assert isinstance(source, dict), "Stored object not a dict"
			self.output_debug("Reading from %s" % (pickle_file, ))
		except (pickle.PickleError, Exception), e:
			source = None
			self.output_info("Error loading %s: %s" % (pickle_file, e))
		return source

	def _pickle_register(self, reg, pickle_file):
		output = open(pickle_file, "wb")
		self.output_debug("Saving to %s" % (pickle_file, ))
		output.write(pickle.dumps(reg, pickle.HIGHEST_PROTOCOL))
		output.close()
		return True

	def _store(self, app_id, application):
		self.register[app_id] = application.get_name()
		self.output_debug("storing application", app_id, "as", application.get_name())
	def _has_match(self, app_id):
		return app_id in self.register

	def _is_match(self, app_id, application):
		return (self._has_match(app_id) and self.register[app_id] == application.get_name()) or (app_id == application.get_name().lower())

	def launched_application(self, app_id):
		if self._has_match(app_id):
			return
		timeout = time() + 15
		envcache = {}
		gobject.timeout_add_seconds(2, self._find_application, app_id, timeout, envcache)
		# and once later
		gobject.timeout_add_seconds(30, self._find_application, app_id, timeout, envcache)

	def _find_application(self, app_id, timeout, envcache=None):
		self.output_debug("Looking for window for application", app_id)
		for w in self._get_wnck_screen_windows_stacked():
			app = w.get_application()
			pid = app.get_pid()
			if not pid:
				pid = w.get_pid()
			env = _read_environ(pid, envcache=envcache)
			if env and kupfer_env in env:
				if env[kupfer_env] == app_id:
					self._store(app_id, app)
					return False
		if time() > timeout:
			return False
		return True

	def application_name(self, app_id):
		if not self._has_match(app_id):
			return None
		return self.register[app_id]

	def application_is_running(self, app_id):
		for w in self._get_wnck_screen_windows_stacked():
			app = w.get_application()
			if app and self._is_match(app_id, app):
				return True
		return False

	def get_application_windows(self, app_id):
		application_windows = []
		for w in self._get_wnck_screen_windows_stacked():
			app = w.get_application()
			if app and self._is_match(app_id, app):
				application_windows.append(w)
		return application_windows

	def application_to_front(self, app_id):
		application_windows = self.get_application_windows(app_id)
		if not application_windows:
			return False

		# for now, just take any window
		evttime = _current_event_time()
		for w in application_windows:
			# we special-case the desktop
			# only show desktop if it's the only window of this app
			if w.get_name() == "x-nautilus-desktop":
				if len(application_windows) == 1:
					screen = wnck.screen_get_default()
					screen.toggle_showing_desktop(True)
				else:
					continue
			wspc = w.get_workspace()
			if wspc:
				wspc.activate(evttime)
			w.activate(evttime)
			break

	def application_close_all(self, app_id):
		application_windows = self.get_application_windows(app_id)
		evttime = _current_event_time()
		for w in application_windows:
			if not w.is_skip_tasklist():
				w.close(evttime)


_appl_match_service = None
def GetApplicationsMatcherService():
	"""Get the (singleton) ApplicationsMatcherService"""
	global _appl_match_service
	if not _appl_match_service:
		_appl_match_service = ApplicationsMatcherService()
	return _appl_match_service

