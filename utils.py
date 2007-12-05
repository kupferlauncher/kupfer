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
