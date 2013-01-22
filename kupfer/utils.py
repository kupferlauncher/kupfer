import itertools
import os
from os import path as os_path
import locale
import signal
import sys

import gobject
import glib


from kupfer import pretty
from kupfer import kupferstring
from kupfer import desktop_launch
from kupfer import launch
from kupfer import desktop_parse
from kupfer import terminal

from kupfer.desktop_launch import SpawnError


def get_dirlist(folder, depth=0, include=None, exclude=None):
	"""
	Return a list of absolute paths in folder
	include, exclude: a function returning a boolean
	def include(filename):
		return ShouldInclude
	"""
	from os import walk
	paths = []
	def include_file(file):
		return (not include or include(file)) and (not exclude or not exclude(file))
		
	for dirname, dirnames, fnames in walk(folder):
		# skip deep directories
		head, dp = dirname, 0
		while not os_path.samefile(head, folder):
			head, tail = os_path.split(head)
			dp += 1
		if dp > depth:
			del dirnames[:]
			continue
		
		excl_dir = []
		for dir in dirnames:
			if not include_file(dir):
				excl_dir.append(dir)
				continue
			abspath = os_path.join(dirname, dir)
			paths.append(abspath)
		
		for file in fnames:
			if not include_file(file):
				continue
			abspath = os_path.join(dirname, file)
			paths.append(abspath)

		for dir in reversed(excl_dir):
			dirnames.remove(dir)

	return paths

def locale_sort(seq, key=unicode):
	"""Return @seq of objects with @key function as a list sorted
	in locale lexical order

	>>> locale.setlocale(locale.LC_ALL, "C")
	'C'
	>>> locale_sort("abcABC")
	['A', 'B', 'C', 'a', 'b', 'c']

	>>> locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
	'en_US.UTF-8'
	>>> locale_sort("abcABC")
	['a', 'A', 'b', 'B', 'c', 'C']
	"""
	locale_cmp = lambda s, o: locale.strcoll(key(s), key(o))
	seq = seq if isinstance(seq, list) else list(seq)
	seq.sort(cmp=locale_cmp)
	return seq

def _argv_to_locale(argv):
	"encode unicode strings in @argv according to the locale encoding"
	return [kupferstring.tolocale(A) if isinstance(A, unicode) else A
			for A in argv]

class AsyncCommand (object):
	"""
	Run a command asynchronously (using the GLib mainloop)

	call @finish_callback when command terminates, or
	when command is killed after @timeout_s seconds, whichever
	comes first.

	If @timeout_s is None, no timeout is used

	If stdin is a byte string, it is supplied on the command's stdin.

	If env is None, command will inherit the parent's environment.

	finish_callback -> (AsyncCommand, stdout_output, stderr_output)

	Attributes:
	self.exit_status  Set after process exited
	self.finished     bool

	"""
	# the maximum input (bytes) we'll read in one shot (one io_callback)
	max_input_buf = 512 * 1024

	def __init__(self, argv, finish_callback, timeout_s, stdin=None, env=None):
		self.stdout = []
		self.stderr = []
		self.stdin = []
		self.timeout = False
		self.killed = False
		self.finished = False
		self.finish_callback = finish_callback

		argv = _argv_to_locale(argv)
		pretty.print_debug(__name__, "AsyncCommand:", argv)

		flags = (glib.SPAWN_SEARCH_PATH | glib.SPAWN_DO_NOT_REAP_CHILD)
		pid, stdin_fd, stdout_fd, stderr_fd = \
		     glib.spawn_async(argv, standard_output=True, standard_input=True,
		                      standard_error=True, flags=flags, envp=env)

		if stdin:
			self.stdin[:] = self._split_string(stdin, self.max_input_buf)
			in_io_flags = glib.IO_OUT | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL
			glib.io_add_watch(stdin_fd, in_io_flags, self._in_io_callback,
			                  self.stdin)
		else:
			os.close(stdin_fd)

		io_flags = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL
		glib.io_add_watch(stdout_fd, io_flags, self._io_callback, self.stdout)
		glib.io_add_watch(stderr_fd, io_flags, self._io_callback, self.stderr)
		self.pid = pid
		glib.child_watch_add(pid, self._child_callback)
		if timeout_s is not None:
			glib.timeout_add_seconds(timeout_s, self._timeout_callback)

	def _split_string(self, s, length):
		"""Split @s in pieces of @length"""
		L = []
		for i in xrange(0, len(s)//length + 1):
			L.append(s[i*length:(i+1)*length])
		return L

	def _io_callback(self, sourcefd, condition, databuf):
		if condition & glib.IO_IN:
			databuf.append(os.read(sourcefd, self.max_input_buf))
			return True
		return False

	def _in_io_callback(self, sourcefd, condition, databuf):
		"""write to child's stdin"""
		if condition & glib.IO_OUT:
			if not databuf:
				os.close(sourcefd)
				return False
			s = databuf.pop(0)
			written = os.write(sourcefd, s)
			if written < len(s):
				databuf.insert(0, s[written:])
			return True
		return False

	def _child_callback(self, pid, condition):
		# @condition is the &status field of waitpid(2) (C library)
		self.exit_status = os.WEXITSTATUS(condition)
		self.finished = True
		self.finish_callback(self, "".join(self.stdout), "".join(self.stderr))

	def _timeout_callback(self):
		"send term signal on timeout"
		if not self.finished:
			self.timeout = True
			os.kill(self.pid, signal.SIGTERM)
			glib.timeout_add_seconds(2, self._kill_callback)

	def _kill_callback(self):
		"Last resort, send kill signal"
		if not self.finished:
			self.killed = True
			os.kill(self.pid, signal.SIGKILL)


def spawn_terminal(workdir=None, screen=None):
	" Raises SpawnError "
	term = terminal.get_configured_terminal()
	notify = term["startup_notify"]
	app_id = term["desktopid"]
	argv = term["argv"]
	desktop_launch.spawn_app_id(app_id, argv, workdir, notify, screen)

def spawn_in_terminal(argv, workdir=None):
	" Raises SpawnError "
	term = terminal.get_configured_terminal()
	notify = term["startup_notify"]
	_argv = list(term["argv"])
	if term["exearg"]:
		_argv.append(term["exearg"])
	_argv.extend(argv)
	desktop_launch.spawn_app_id(term["desktopid"], _argv , workdir, notify)

def spawn_async_notify_as(app_id, argv):
	"""
	Spawn argument list @argv and startup-notify as
	if application @app_id is starting (if possible)

	raises SpawnError
	"""
	desktop_launch.spawn_app_id(app_id, argv , None, True)

def spawn_async(argv, in_dir="."):
	"""
	Silently spawn @argv in the background

	Returns False on failure
	"""
	try:
		return spawn_async_raise(argv, in_dir)
	except SpawnError as exc:
		pretty.print_debug(__name__, "spawn_async", argv, exc)
		return False

def spawn_async_raise(argv, workdir="."):
	"""
	A version of spawn_async that raises on error.

	raises SpawnError
	"""
	argv = _argv_to_locale(argv)
	pretty.print_debug(__name__, "spawn_async", argv, workdir)
	try:
		return gobject.spawn_async (argv, working_directory=workdir,
				flags=gobject.SPAWN_SEARCH_PATH)
	except gobject.GError as exc:
		raise SpawnError(exc)

def argv_for_commandline(cli):
	return desktop_parse.parse_argv(cli)

def launch_commandline(cli, name=None, in_terminal=False):
	" Raises SpawnError "
	argv = desktop_parse.parse_argv(cli)
	pretty.print_error(__name__, "Launch commandline is deprecated ")
	pretty.print_debug(__name__, "Launch commandline (in_terminal=", in_terminal, "):", argv, sep="")
	if in_terminal:
		return spawn_in_terminal(argv)
	return spawn_async(argv)

def launch_app(app_info, files=(), uris=(), paths=()):
	" Raises SpawnError "

	# With files we should use activate=False
	return launch.launch_application(app_info, files, uris, paths,
			activate=False)

def show_path(path):
	"""Open local @path with default viewer"""
	from gio import File
	# Implemented using gtk.show_uri
	gfile = File(path)
	if not gfile:
		return
	url = gfile.get_uri()
	show_url(url)

def show_url(url):
	"""Open any @url with default viewer"""
	from gtk import show_uri, get_current_event_time
	from gtk.gdk import screen_get_default
	from glib import GError
	try:
		pretty.print_debug(__name__, "show_url", url)
		return show_uri(screen_get_default(), url, get_current_event_time())
	except GError, exc:
		pretty.print_error(__name__, "gtk.show_uri:", exc)

def _on_child_exit(pid, condition, user_data):
	# @condition is the &status field of waitpid(2) (C library)
	argv, respawn = user_data
	if respawn:
		is_signal = os.WIFSIGNALED(condition)
		if is_signal and respawn:
			def callback(*args):
				spawn_child(*args)
				return False
			glib.timeout_add_seconds(10, callback, argv, respawn)

def _try_register_pr_pdeathsig():
    """
    Register PR_SET_PDEATHSIG (linux-only) for the calling process
    which is a signal delivered when its parent dies.

    This should ensure child processes die with the parent.
    """
    PR_SET_PDEATHSIG=1
    SIGHUP=1
    if sys.platform != 'linux2':
        return
    try:
        import ctypes
    except ImportError:
        return
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(PR_SET_PDEATHSIG, SIGHUP)
    except (AttributeError, OSError):
        pass

def spawn_child(argv, respawn=True, display=None):
	"""
	Spawn argv in the mainloop and keeping it as a child process
	(it will be made sure to exit with the parent).

	@respawn: If True, respawn if child dies abnormally

	raises utils.SpawnError
	returns pid
	"""
	flags = (glib.SPAWN_SEARCH_PATH | glib.SPAWN_DO_NOT_REAP_CHILD)
	kwargs = {}
	if display:
		# environment is passed as a sequence of strings
		envd = os.environ.copy()
		envd['DISPLAY'] = display
		kwargs['envp'] = ['='.join((k,v)) for k,v in envd.items()]

	try:
		pid, stdin_fd, stdout_fd, stderr_fd = \
			glib.spawn_async(argv, flags=flags,
			                 child_setup=_try_register_pr_pdeathsig,
			                 **kwargs)
	except glib.GError as exc:
		raise utils.SpawnError(unicode(exc))
	if pid:
		glib.child_watch_add(pid, _on_child_exit, (argv, respawn))
	return pid

def start_plugin_helper(name, respawn, display=None):
	"""
	@respawn: If True, respawn if child dies abnormally

	raises SpawnError
	"""
	argv = [sys.executable]
	argv.extend(sys.argv)
	argv.append('--exec-helper=%s' % name)
	pretty.print_debug(__name__, "Spawning", argv)
	return spawn_child(argv, respawn, display=display)

def show_help_url(url):
	"""
	Try at length to display a startup notification for the help browser.

	Return False if there is no handler for the help URL
	"""
	import gio
	## Check that the system help viewer is Yelp,
	## and if it is, launch its startup notification.
	scheme = gio.File(url).get_uri_scheme()
	default = gio.app_info_get_default_for_uri_scheme(scheme)
	help_viewer_id = "yelp.desktop"
	if not default:
		return False
	try:
		yelp = gio.unix.DesktopAppInfo(help_viewer_id)
	except RuntimeError:
		return show_url(url)
	cmd_path = lookup_exec_path(default.get_executable())
	yelp_path = lookup_exec_path(yelp.get_executable())
	if cmd_path and yelp_path and os.path.samefile(cmd_path, yelp_path):
		try:
			spawn_async_notify_as(help_viewer_id, [cmd_path, url])
			return True
		except SpawnError:
			pass
	return show_url(url)

def lookup_exec_path(exename):
	"Return path for @exename in $PATH or None"
	PATH = os.environ.get("PATH") or os.defpath
	for execdir in PATH.split(os.pathsep):
		exepath = os.path.join(execdir, exename)
		if os.access(exepath, os.R_OK|os.X_OK) and os.path.isfile(exepath):
			return exepath

def is_directory_writable(dpath):
	"""If directory path @dpath is a valid destination to write new files?
	"""
	if not os_path.isdir(dpath):
		return False
	return os.access(dpath, os.R_OK | os.W_OK | os.X_OK)

def get_destpath_in_directory(directory, filename, extension=None):
	"""Find a good destpath for a file named @filename in path @directory
	Try naming the file as filename first, before trying numbered versions
	if the previous already exist.

	If @extension, it is used as the extension. Else the filename is split and
	the last extension is used
	"""
	# find a nonexisting destname
	ctr = itertools.count(1)
	basename = filename + (extension or "")
	destpath = os_path.join(directory, basename)
	while True:
		if not os_path.exists(destpath):
			break
		if extension:
			root, ext = filename, extension
		else:
			root, ext = os_path.splitext(filename)
		basename = "%s-%s%s" % (root, ctr.next(), ext)
		destpath = os_path.join(directory, basename)
	return destpath

def get_destfile_in_directory(directory, filename, extension=None):
	"""Find a good destination for a file named @filename in path @directory.

	Like get_destpath_in_directory, but returns an open file object, opened
	atomically to avoid race conditions.

	Return (fileobj, filepath)
	"""
	# retry if it fails
	for retry in xrange(3):
		destpath = get_destpath_in_directory(directory, filename, extension)
		try:
			fd = os.open(destpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0666)
		except OSError, exc:
			pretty.print_error(__name__, exc)
		else:
			return (os.fdopen(fd, "wb"), destpath)
	return (None, None)

def get_safe_tempfile():
	"""Return (fileobj, filepath) pointing to an open temporary file"""
	import tempfile
	fd, path = tempfile.mkstemp()
	return (os.fdopen(fd, "wb"), path)

def get_display_path_for_bytestring(filepath):
	"""Return a unicode path for display for bytestring @filepath

	Will use glib's filename decoding functions, and will
	format nicely (denote home by ~/ etc)
	"""
	desc = gobject.filename_display_name(filepath)
	homedir = os.path.expanduser("~/")
	if desc.startswith(homedir) and homedir != desc:
		desc = desc.replace(homedir, "~/", 1)
	return desc

def parse_time_interval(tstr):
	"""
	Parse a time interval in @tstr, return whole number of seconds

	>>> parse_time_interval("2")
	2
	>>> parse_time_interval("1h 2m 5s")
	3725
	>>> parse_time_interval("2 min")
	120
	"""
	weights = {
		"s": 1, "sec": 1,
		"m": 60, "min": 60,
		"h": 3600, "hours": 3600,
	}
	try:
		return int(tstr)
	except ValueError:
		pass

	total = 0
	amount = 0
	# Split the string in runs of digits and runs of characters
	for isdigit, group in itertools.groupby(tstr, lambda k: k.isdigit()):
		part = "".join(group).strip()
		if not part:
			continue
		if isdigit:
			amount = int(part)
		else:
			total += amount * weights.get(part.lower(), 0)
			amount = 0
	return total


if __name__ == '__main__':
	import doctest
	doctest.testmod()
