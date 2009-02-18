from os import path

icon_cache = {}

def get_icon(key):
	"""
	try retrieve icon in cache
	is a generator so it can be concisely called with a for loop
	"""
	if key not in icon_cache:
		return
	rec = icon_cache[key]
	rec["accesses"] += 1
	yield rec["icon"]

def store_icon(key, icon):
	if key in icon_cache:
		raise Exception("already in cache")
	icon_rec = {"icon":icon, "accesses":0}
	icon_cache[key] = icon_rec


def get_icon_for_uri(uri, icon_size):
	"""
	Return a pixbuf representing the file at
	the URI generally (mime-type based)

	return None if not found
	
	@param icon_size: a pixel size of the icon
	@type icon_size: an integer object.
	 
	"""
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gnomevfs import get_mime_type, exists
	from gnome.ui import ThumbnailFactory, icon_lookup

	if not exists(uri):
		return None

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
