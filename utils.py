import gnomevfs
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
		while head != folder:
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

def get_icon_for_uri(uri, icon_size=48):
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

def get_icon_for_name(icon_name, icon_size=48):
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gobject import GError
	icon_theme = icon_theme_get_default()
	try:
		icon = icon_theme.load_icon(icon_name, icon_size, ICON_LOOKUP_USE_BUILTIN)
	except GError:
		return None
	return icon

def get_application_icon(app_spec=None, icon_size=48):
	# known application names
	known = {
		"gedit": "text-editor",
		"yelp" : "help-browser",
	}
	if not app_spec:
		return get_icon_for_name("exec", icon_size)
	name = ((app_spec[2]).split())[0]
	if "/" in name:
		from os import path
		(head, tail) = path.split(name)
		if tail:
			name = tail
	if name in known:
		name = known[name]
	icon = get_icon_for_name(name, icon_size)
	if icon: print "foudn icon", icon, "for", name, "size", (icon.get_width(), icon.get_height())
	if icon: 
		if icon_size/2 <= icon.get_width() < icon_size:
			import gtk.gdk
			icon = icon.scale_simple(icon_size, icon_size, gtk.gdk.INTERP_BILINEAR)
		elif icon.get_width() < icon_size/2:
			icon = None

	if not icon:
		print "No icon found for", name
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

