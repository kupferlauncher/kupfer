import wnck
import gtk
import gobject
from time import time
import os
from os import path

import cPickle as pickle

from kupfer import pretty, config
from kupfer import scheduler

kupfer_env = "KUPFER_APP_ID"

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
	if envcache: envcache[pid] = env
	return environ

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

	# launch on current workspace
	workspace = wnck.screen_get_default().get_active_workspace()
	nbr = workspace.get_number() if workspace else -1
	ctx.set_desktop(nbr)
	ctx.set_timestamp(gtk.get_current_event_time())

	if track:
		app_id = app_info.get_id()
		os.putenv(kupfer_env, app_id)
	else:
		app_id = ""
	svc = GetApplicationsMatcherService()
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
			svc.launched_application(app_info.get_id())
	finally:
		os.unsetenv(kupfer_env)
	return True

def application_is_running(app_info):
	svc = GetApplicationsMatcherService()
	return svc.application_is_running(app_info.get_id())

class ApplicationsMatcherService (pretty.OutputMixin):
	"""Handle launching applications and see if they still run.
	This is a learning service, since we have no first-class application
	object on the Linux desktop
	"""
	def __init__(self):
		self.register = {}
		screen = wnck.screen_get_default()
		screen.get_windows_stacked()
		scheduler.GetScheduler().connect("finish", self._finish)
		self._load()

	def _get_filename(self):
		version = 1
		return path.join(config.get_cache_home(),
				"application_identification_v%d.pickle" % version)
	def _load(self):
		reg = self._unpickle_register(self._get_filename())
		self.register = reg if reg else {}
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
		self.output_debug("storing", app_id, "as", application.get_name())
	def _has_match(self, app_id):
		return app_id in self.register
	def _is_match(self, app_id, application):
		if not self._has_match(app_id):
			return False
		return self.register[app_id] == application.get_name()

	def launched_application(self, app_id):
		if self._has_match(app_id):
			return
		timeout = time() + 10
		envcache = {}
		gobject.timeout_add_seconds(2, self._find_application, app_id, timeout, envcache)

	def _find_application(self, app_id, timeout, envcache=None):
		screen = wnck.screen_get_default()
		for w in screen.get_windows_stacked():
			app = w.get_application()
			pid = app.get_pid()
			if not pid:
				pid = w.get_pid()
			self.output_debug("App %s has pid %d" %( app.get_name(), pid))
			env = _read_environ(pid, envcache=envcache)
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

