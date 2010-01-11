import itertools
import os
from os import path as os_path
import locale

import gobject

from kupfer import pretty

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

def spawn_async(argv, in_dir="."):
	pretty.print_debug(__name__, "Spawn commandline", argv, in_dir)
	try:
		return gobject.spawn_async (argv, working_directory=in_dir,
				flags=gobject.SPAWN_SEARCH_PATH)
	except gobject.GError, exc:
		pretty.print_debug(__name__, "spawn_async", argv, exc)

def app_info_for_commandline(cli, name=None, in_terminal=False):
	import gio
	flags = gio.APP_INFO_CREATE_NEEDS_TERMINAL if in_terminal else gio.APP_INFO_CREATE_NONE
	if not name:
		name = cli
	item = gio.AppInfo(cli, name, flags)
	return item

def launch_commandline(cli, name=None, in_terminal=False):
	from kupfer import launch
	app_info = app_info_for_commandline(cli, name, in_terminal)
	pretty.print_debug(__name__, "Launch commandline (in_terminal=", in_terminal, "):", cli, sep="")
	return launch.launch_application(app_info, activate=False, track=False)

def launch_app(app_info, files=(), uris=(), paths=()):
	from kupfer import launch

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

def _tolocale(ustr):
	import locale
	enc = locale.getpreferredencoding(do_setlocale=False)
	if isinstance(ustr, unicode):
		return ustr.encode(enc, "replace")
	return ustr

def show_url_xdg(url):
	"""Open @url xdg-open"""
	pretty.print_debug(__name__, "show_url_xdg", url)
	encoded_url = _tolocale(url)
	return spawn_async(("xdg-open", encoded_url))

def show_url(url):
	"""Open any @url with default viewer"""
	return show_url_xdg(url)
	from gtk import show_uri, get_current_event_time
	from gtk.gdk import screen_get_default
	from glib import GError
	try:
		pretty.print_debug(__name__, "show_url", url)
		return show_uri(screen_get_default(), url, get_current_event_time())
	except GError, exc:
		pretty.print_error(__name__, "gtk.show_uri:", exc)

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
