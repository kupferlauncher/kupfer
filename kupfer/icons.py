from os import path
from gtk import icon_theme_get_default

icon_cache = {}

def _icon_theme_changed(theme):
	print "Icon theme changed, clearing cache"
	global icon_cache
	icon_cache = {}

_default_theme = icon_theme_get_default()
_default_theme.connect("changed", _icon_theme_changed)

# Fix bad icon names
# for example, gio returns "inode-directory" for folders
icon_name_translation = {
		"inode-directory": "folder",
		}

def get_icon(key):
	"""
	try retrieve icon in cache
	is a generator so it can be concisely called with a for loop
	"""
	rec = icon_cache.get(key, None)
	if not rec:
		return
	rec["accesses"] += 1
	yield rec["icon"]

def store_icon(key, icon):
	"""
	Store an icon in cache. It must not have been stored before
	"""
	assert key not in icon_cache, "icon %s already in cache" % key
	assert icon, "icon %s may not be %s" % (key, icon)
	icon_rec = {"icon":icon, "accesses":0}
	icon_cache[key] = icon_rec

def get_thumbnail_for_file(uri, width=-1, height=-1):
	"""
	Return a Pixbuf thumbnail for the file at
	the @uri, which can be *either* and uri or a path
	size is @width x @height

	return None if not found
	"""
	from gio import File, FILE_ATTRIBUTE_THUMBNAIL_PATH, FileIcon
	from gtk.gdk import pixbuf_new_from_file_at_size
	from gobject import GError

	gfile = File(uri)
	if not gfile.query_exists():
		return None
	finfo = gfile.query_info(FILE_ATTRIBUTE_THUMBNAIL_PATH)
	thumb_path = finfo.get_attribute_byte_string(FILE_ATTRIBUTE_THUMBNAIL_PATH)
	if not thumb_path:
		return None
	try:
		icon = pixbuf_new_from_file_at_size(thumb_path, width, height)
		return icon
	except GError, e:
		print "get_thumbnail_for_file, error:", e
		return None

def get_gicon_for_file(uri):
	"""
	Return a GIcon representing the file at
	the @uri, which can be *either* and uri or a path

	return None if not found
	"""
	from gio import File, FILE_ATTRIBUTE_STANDARD_ICON

	gfile = File(uri)
	if not gfile.query_exists():
		return None

	finfo = gfile.query_info(FILE_ATTRIBUTE_STANDARD_ICON)
	gicon = finfo.get_attribute_object(FILE_ATTRIBUTE_STANDARD_ICON)
	return gicon

def get_icon_for_gicon(gicon, icon_size):
	"""
	Return a pixbuf of @icon_size for the @gicon

	NOTE: Currently only ThemedIcon or FileIcon
	can be rendered
	"""
	# FIXME: We can't load any general GIcon
	if not gicon:
		return None
	from gio import ThemedIcon, FileIcon
	if isinstance(gicon, FileIcon):
		ifile = gicon.get_file()
		return get_icon_from_file(ifile.get_path(), icon_size)
	if isinstance(gicon, ThemedIcon):
		names = gicon.get_names()
		return get_icon_for_name(names[0], icon_size, names)
	print "get_icon_for_gicon, could not load", gicon
	return None

def get_icon_for_file(uri, icon_size):
	"""
	Return a pixbuf representing the file at
	the @uri, which can be *either* and uri or a path

	return None if not found
	
	@icon_size: a pixel size of the icon
	"""
	from gio import File, FILE_ATTRIBUTE_STANDARD_ICON

	gfile = File(uri)
	if not gfile.query_exists():
		return None

	finfo = gfile.query_info(FILE_ATTRIBUTE_STANDARD_ICON)
	gicon = finfo.get_attribute_object(FILE_ATTRIBUTE_STANDARD_ICON)
	return get_icon_for_gicon(gicon, icon_size)

def get_icon_for_name(icon_name, icon_size, icon_names=[]):
	for i in get_icon(icon_name):
		return i
	from gtk import ICON_LOOKUP_USE_BUILTIN, ICON_LOOKUP_FORCE_SIZE
	from gobject import GError
	if not icon_names: icon_names = (icon_name,)

	# Try the whole list of given names
	for load_name in icon_names:
		# Possibly use a different name for lookup
		if load_name in icon_name_translation:
			load_name = icon_name_translation[load_name]
		try:
			icon = _default_theme.load_icon(load_name, icon_size, ICON_LOOKUP_USE_BUILTIN | ICON_LOOKUP_FORCE_SIZE)
			if icon:
				break
		except GError, e:
			icon = None
		except Exception, e:
			print "get_icon_for_name, error:", e
			icon = None
	else:
		# if we did not reach 'break' in the loop
		return None
	# We store the first icon in the list, even if the match
	# found was later in the chain
	store_icon(icon_name, icon)
	return icon

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
	except GError, e:
		print "get_icon_from_file, error:", e
		return None

def get_good_name_for_icon_names(names):
	"""Return first name in @names that exists
	in current icon theme, or None
	"""
	for name in names:
		if _default_theme.has_icon(name):
			return name
	return None
