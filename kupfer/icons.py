from os import path
from gtk import icon_theme_get_default, icon_theme_add_builtin_icon
from gtk.gdk import pixbuf_new_from_file_at_size
from gio import ThemedIcon, Icon, FileIcon

from kupfer import config, pretty, scheduler

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

def load_kupfer_icons(sched=None):
	"""Load in kupfer icons from installed files"""
	ilist = "art/icon-list"
	ilist_file_path = config.get_data_file(ilist)
	if not ilist_file_path:
		pretty.print_info(__name__, "Datafile %s not found" % ilist)
		return
	# parse icon list file
	ifile = open(ilist_file_path, "r")
	for line in ifile:
		# ignore '#'-comments
		if line.startswith("#"):
			continue
		icon_name, basename, size = (i.strip() for i in line.split("\t", 2))
		size = int(size)
		icon_path = config.get_data_file(path.join("art", basename))
		if not icon_path:
			pretty.print_info(__name__, "Icon", basename,icon_path,"not found")
			continue
		pixbuf = pixbuf_new_from_file_at_size(icon_path, size,size)
		icon_theme_add_builtin_icon(icon_name, size, pixbuf)
		pretty.print_debug(__name__, "Loading icon", icon_name, "at", size,
				"from", icon_path)

sch = scheduler.GetScheduler()
sch.connect("load", load_kupfer_icons)

def get_icon(key, icon_size):
	"""
	try retrieve icon in cache
	is a generator so it can be concisely called with a for loop
	"""
	rec = icon_cache.get(icon_size, {}).get(key, None)
	if not rec:
		return
	rec["accesses"] += 1
	yield rec["icon"]

def store_icon(key, icon_size, icon):
	"""
	Store an icon in cache. It must not have been stored before
	"""
	assert key not in icon_cache.get(icon_size, ()), \
		"icon %s already in cache" % key
	assert icon, "icon %s may not be %s" % (key, icon)
	icon_rec = {"icon":icon, "accesses":0}
	if icon_size not in icon_cache: icon_cache[icon_size] = {}
	icon_cache[icon_size][key] = icon_rec

def _get_icon_dwim(icon, icon_size):
	"""Make an icon at @icon_size where
	@icon can be either an icon name, or a gicon
	"""
	from gio import Icon
	if isinstance(icon, Icon):
		return get_icon_for_gicon(icon, icon_size)
	elif icon:
		return get_icon_for_name(icon, icon_size)
	return None

class ComposedIcon (Icon):
	"""
	A composed icon, which kupfer will render to pixbuf as
	background icon with the decorating icon as emblem

	@minimum_icon_size is the minimum size for
	the composition to be drawn
	"""
	minimum_icon_size = 48
	def __new__(cls, baseicon, emblemicon, emblem_is_fallback=False):
		fallback_icon = emblemicon if emblem_is_fallback else baseicon
		if isinstance(fallback_icon, (basestring, ThemedIcon)):
			return _ComposedThemedIcon(baseicon, emblemicon, emblem_is_fallback)
		if isinstance(fallback_icon, FileIcon):
			return _ComposedFileIcon(baseicon, emblemicon, emblem_is_fallback)
		return None

class _ComposedIconImpl (object):
	def __init__(self, baseicon, emblemicon, emblem_is_fallback):
		self.baseicon = baseicon
		self.emblemicon = emblemicon
		self.fallback_icon = emblemicon if emblem_is_fallback else baseicon

class _ComposedThemedIcon (_ComposedIconImpl, ThemedIcon):
	def __init__(self, baseicon, emblemicon, emblem_is_fallback):
		_ComposedIconImpl.__init__(self, baseicon, emblemicon,
				emblem_is_fallback)
		if isinstance(self.fallback_icon, basestring):
			names = (self.fallback_icon, )
		else:
			names = self.fallback_icon.get_names()
		ThemedIcon.__init__(self, names)

class _ComposedFileIcon (_ComposedIconImpl, FileIcon):
	def __init__(self, baseicon, emblemicon, emblem_is_fallback):
		_ComposedIconImpl.__init__(self, baseicon, emblemicon,
				emblem_is_fallback)
		FileIcon.__init__(self, self.fallback_icon.get_file())

def _render_composed_icon(composed_icon, icon_size):
	import gtk
	# If it's too small, render as fallback icon
	if icon_size < ComposedIcon.minimum_icon_size:
		return _get_icon_for_standard_gicon(composed_icon, icon_size)
	emblemicon = composed_icon.emblemicon
	baseicon = composed_icon.baseicon
	toppbuf = _get_icon_dwim(emblemicon, icon_size)
	bottompbuf = _get_icon_dwim(baseicon, icon_size)
	if not toppbuf or not bottompbuf:
		return None

	dest = bottompbuf.copy()
	# @fr is the scale
	fr = 0.6
	dcoord = int((1-fr)*icon_size)
	dsize = int(fr*icon_size)
	# http://library.gnome.org/devel/gdk-pixbuf/unstable//gdk-pixbuf-scaling.html
	toppbuf.composite(dest, dcoord, dcoord, dsize, dsize,
			dcoord, dcoord, fr, fr, gtk.gdk.INTERP_BILINEAR, 255)
	return dest

def get_thumbnail_for_file(uri, width=-1, height=-1):
	"""
	Return a Pixbuf thumbnail for the file at
	the @uri, which can be *either* and uri or a path
	size is @width x @height

	return None if not found
	"""
	from gio import File, FILE_ATTRIBUTE_THUMBNAIL_PATH, FileIcon

	gfile = File(uri)
	if not gfile.query_exists():
		return None
	finfo = gfile.query_info(FILE_ATTRIBUTE_THUMBNAIL_PATH)
	thumb_path = finfo.get_attribute_byte_string(FILE_ATTRIBUTE_THUMBNAIL_PATH)

	return get_pixbuf_from_file(thumb_path, width, height)

def get_pixbuf_from_file(thumb_path, width=-1, height=-1):
	"""
	Return a Pixbuf thumbnail for the file at @thumb_path
	sized @width x @height
	For non-icon pixbufs:
	We might cache these, but on different terms than the icon cache
	if @thumb_path is None, return None
	"""
	from gobject import GError
	if not thumb_path:
		return None
	try:
		icon = pixbuf_new_from_file_at_size(thumb_path, width, height)
		return icon
	except GError, e:
		# this error is not important, the program continues on fine,
		# so we put it in debug output.
		pretty.print_debug(__name__, "get_pixbuf_from_file file:", thumb_path,
			"error:", e)

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

	NOTE: Currently only the following can be rendered:
		gio.ThemedIcon
		gio.FileIcon
		kupfer.icons.ComposedIcon
	"""
	# FIXME: We can't load any general GIcon
	if not gicon:
		return None
	if isinstance(gicon, _ComposedIconImpl):
		return _render_composed_icon(gicon, icon_size)
	return _get_icon_for_standard_gicon(gicon, icon_size)

def _get_icon_for_standard_gicon(gicon, icon_size):
	"""Render ThemedIcon and FileIcon"""
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
	for i in get_icon(icon_name, icon_size):
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
	store_icon(icon_name, icon_size, icon)
	return icon

def get_icon_from_file(icon_file, icon_size):
	# try to load from cache
	for icon in get_icon(icon_file, icon_size):
		return icon

	from gobject import GError
	try:
		icon = pixbuf_new_from_file_at_size(icon_file, icon_size, icon_size)
		store_icon(icon_file, icon_size, icon)
		return icon
	except GError, e:
		print "get_icon_from_file, error:", e
		return None

def is_good(gicon):
	"""Return True if it is likely that @gicon will load a visible icon
	(icon name exists in theme, or icon references existing file)
	"""
	if not gicon:
		return False
	if isinstance(gicon, ThemedIcon):
		return bool(get_good_name_for_icon_names(gicon.get_names()))
	if isinstance(gicon, FileIcon):
		ifile = gicon.get_file()
		return ifile.query_exists()
	# Since we can't load it otherwise (right now, see above)
	return False

def get_gicon_with_fallbacks(gicon, names):
	if not is_good(gicon):
		for name in names:
			gicon = ThemedIcon(name)
			if is_good(gicon):
				return gicon
		return ThemedIcon(name)
	return gicon

def get_good_name_for_icon_names(names):
	"""Return first name in @names that exists
	in current icon theme, or None
	"""
	for name in names:
		if _default_theme.has_icon(name):
			return name
	return None
