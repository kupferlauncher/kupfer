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

def new_desktop_item(exec_path, in_terminal=False):
	"""
	Return a new desktop item with given exec_path

	It will set name from the path, and set the item to to
	Application. Some additional properties can be set too.
	"""
	from gnomedesktop import item_new_from_string
	import gnomedesktop as gd
	name = path.basename(exec_path)

	# Do escaping
	# Escape \ " ` $ with another \
	# and enclose in ""
	bsl, quot = "\\", '"'
	esc_chars = (bsl, quot, '`', '$')
	escaped = [bsl*(c in esc_chars) + c for c in unicode(exec_path)]
	escaped.insert(0, quot)
	escaped.append(quot)
	exec_path_escaped = u"".join(escaped)

	item = gd.DesktopItem()
	item.set_entry_type(gd.TYPE_APPLICATION)
	item.set_string(gd.KEY_NAME, name)
	item.set_string(gd.KEY_EXEC, exec_path_escaped)
	item.set_boolean(gd.KEY_TERMINAL, in_terminal)
	return item
