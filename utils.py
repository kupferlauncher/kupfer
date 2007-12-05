from os import path

import atexit

icon_cache = {}

def icon_stats():
	c = 0
	tot_acc = 0
	tot_pix = 0
	for k in icon_cache:
		rec = icon_cache[k]
		acc = rec["accesses"]
		if not acc:
			c += 1
		tot_acc += acc
		icon = rec["icon"]
		tot_pix += icon.get_height() * icon.get_width()
	print "Cached icons:",  len(icon_cache)
	print "Unused cache entries", len(icon_cache) -c
	print "Total accesses", tot_acc
	print "Sum pixels", tot_pix

atexit.register(icon_stats)

def get_icon(key):
	"""
	try retrieve icon in cache
	is a generator so it can be concisely called with a for loop
	"""
	if key not in icon_cache:
		return
	print "Retrieved icon", key
	rec = icon_cache[key]
	rec["accesses"] += 1
	yield rec["icon"]

def store_icon(key, icon):
	if key in icon_cache:
		raise Exception("already in cache")
	icon_rec = {"icon":icon, "accesses":0}
	icon_cache[key] = icon_rec
	print "Loaded icon", key


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

def get_icon_for_uri(uri, icon_size):
	"""
	Return a pixbuf representing the file at
	the URI generally (mime-type based)

	return None if not found
	
	@param icon_size: a pixel size of the icon
	@type icon_size: an integer object.
	 
	"""
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gnomevfs import get_mime_type
	from gnome.ui import ThumbnailFactory, icon_lookup

	mtype = get_mime_type(uri)
	icon_theme = icon_theme_get_default()
	thumb_factory = ThumbnailFactory(16)
	icon_name, num = icon_lookup(icon_theme, thumb_factory,  file_uri=uri, custom_icon="")
	return get_icon_for_name(icon_name, icon_size)

def get_icon_for_name(icon_name, icon_size):
	for i in get_icon(icon_name):
		return i
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gobject import GError
	icon_theme = icon_theme_get_default()
	try:
		icon = icon_theme.load_icon(icon_name, icon_size, ICON_LOOKUP_USE_BUILTIN)
	except GError:
		return None
	store_icon(icon_name, icon)
	return icon

def get_icon_for_desktop_file(desktop_file, icon_size):
	"""
	Return the icon of a given desktop file path
	"""
	from gnomedesktop import item_new_from_file, LOAD_ONLY_IF_EXISTS
	desktop_item = item_new_from_file(desktop_file, LOAD_ONLY_IF_EXISTS)

	return get_icon_for_desktop_item(desktop_item, icon_size)

def get_icon_for_desktop_name(desktop_name, icon_size):
	"""
	Return the icon of a desktop item given its basename
	"""
	for icon in get_icon(desktop_name):
		return icon
	from gnomedesktop import item_new_from_basename, LOAD_ONLY_IF_EXISTS
	desktop_item = item_new_from_basename(desktop_file, LOAD_ONLY_IF_EXISTS)

	icon = get_icon_for_desktop_item(desktop_item, icon_size)
	store_icon(desktop_name, icon)
	return icon

def get_icon_for_desktop_item(desktop_item, icon_size):
	"""
	Return the pixbuf of a given desktop item

	Use some hackery. Take the icon directly if it is absolutely given,
	otherwise use the name minus extension from current icon theme
	"""
	from gtk import icon_theme_get_default
	from gnomedesktop import find_icon, LOAD_ONLY_IF_EXISTS, KEY_ICON
	icon_name = desktop_item.get_string(KEY_ICON)
	if not icon_name:
		return None

	if not path.isabs(icon_name):
		icon_name, extension = path.splitext(icon_name)
		icon_info = icon_theme_get_default().lookup_icon(icon_name, icon_size, 0)
		if icon_info:
			icon_file = icon_info.get_filename()
		else:
			icon_file = None
	else:
		icon_file = icon_name

	if not icon_file:
		return None
	return get_icon_from_file(icon_file, icon_size)


def get_icon_from_file(icon_file, icon_size):
	# try to load from cache
	for icon in get_icon(icon_file):
		return icon

	from gtk.gdk import pixbuf_new_from_file_at_size
	from gobject import GError
	try:
		icon = pixbuf_new_from_file_at_size(icon_file, icon_size, icon_size)
		store_icon(icon_file, icon)
		return icon
	except GError, info:
		print info
		return None

def get_default_application_icon(icon_size):
	icon = get_icon_for_name("exec", icon_size)
	return icon

def spawn_async(argv, in_dir=None):
	import gobject
	from os import chdir, getcwd
	if in_dir:
		oldwd = getcwd()
		chdir(in_dir)
	ret = gobject.spawn_async (argv, flags=gobject.SPAWN_SEARCH_PATH)
	if in_dir:
		chdir(oldwd)

def get_xdg_data_dirs():
	"""
	Return a list of XDG data directories

	From the deskbar applet project
	"""
	import os

	dirs = os.getenv("XDG_DATA_HOME")
	if dirs == None:
		dirs = os.path.expanduser("~/.local/share")
	
	sysdirs = os.getenv("XDG_DATA_DIRS")
	if sysdirs == None:
		sysdirs = "/usr/local/share:/usr/share"
	
	dirs = "%s:%s" % (dirs, sysdirs)
	return [dir for dir in dirs.split(":") if dir.strip() != "" and path.exists(dir)]

def new_desktop_item(exec_path):
	"""
	Return a new desktop item with given exec_path (and name from that) 
	type Application. The rest can be set with .set_string()
	on the returned object
	"""
	from gnomedesktop import item_new_from_string, KEY_TERMINAL
	name = path.basename(exec_path)
	props = {
			"Type":"Application",
			"Exec":exec_path,
			"Name":name
		}
	desktop_string = """[Desktop Entry]
Encoding=UTF-8
"""
	desktop_string += "\n".join("%s=%s" % (k,v ) for k,v in props.items())
	print desktop_string
	
	desktop_item = item_new_from_string("", desktop_string, len(desktop_string), 0)  
	return desktop_item
