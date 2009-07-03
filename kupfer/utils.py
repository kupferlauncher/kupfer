from os import path


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
		while not path.samefile(head, folder):
			head, tail = path.split(head)
			dp += 1
		if dp > depth:
			del dirnames[:]
			continue
		
		excl_dir = []
		for dir in dirnames:
			if not include_file(dir):
				excl_dir.append(dir)
				continue
			abspath = path.join(dirname, dir)
			paths.append(abspath)
		
		for file in fnames:
			if not include_file(file):
				continue
			abspath = path.join(dirname, file)
			paths.append(abspath)

		for dir in reversed(excl_dir):
			dirnames.remove(dir)

	return paths

def spawn_async(argv, in_dir=None):
	import gobject
	from os import chdir, getcwd
	if in_dir:
		oldwd = getcwd()
		chdir(in_dir)
	ret = gobject.spawn_async (argv, flags=gobject.SPAWN_SEARCH_PATH)
	if in_dir:
		chdir(oldwd)

def app_info_for_commandline(cli, name=None, in_terminal=False):
	import gio
	flags = gio.APP_INFO_CREATE_NEEDS_TERMINAL if in_terminal else gio.APP_INFO_CREATE_NONE
	if not name:
		name = cli
	item = gio.AppInfo(cli, name, flags)
	return item

def launch_commandline(cli, name=None, in_terminal=False):
	return launch_app(app_info_for_commandline(cli, name, in_terminal))

def launch_app(app_info, files=(), uris=(), paths=()):
	"""
	Launch @app_info correctly, using a startup notification

	you may pass in either a list of gio.Files in @files, or 
	a list of @uris or @paths
	"""
	assert app_info
	from gtk.gdk import AppLaunchContext
	from gio import File
	ctx = AppLaunchContext()
	if paths:
		files = [File(p) for p in paths]
	from glib import GError
	try:
		if uris:
			ret = app_info.launch_uris(uris, ctx)
		else:
			ret = app_info.launch(files, ctx)
		if not ret:
			print "Error when launching", app_info
	except GError, e:
		print "launch_app:", e
		return False
	return True

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
		show_uri(screen_get_default(), url, get_current_event_time())
	except GError, e:
		print "Error in gtk.show_uri:", e
