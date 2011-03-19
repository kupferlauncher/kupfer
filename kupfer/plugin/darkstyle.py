__kupfer_name__ = _("Dark Theme")
__kupfer_sources__ = ()
__description__ = _("Use a dark color theme")
__version__ = ""
__author__ = ""

import os
import gtk

from kupfer import config

DARK_STYLE = """
style "dark"
{
	## bg: background color
	bg[NORMAL] = "#333"
	bg[SELECTED] = "#000"
	bg[ACTIVE] = "#222"
	bg[PRELIGHT] = "#222"
	bg[INSENSITIVE] = "#333"

	## fg: foreground text color
	fg[NORMAL] = "#DDD"
	fg[SELECTED] = "#EEE"
	fg[ACTIVE] = "#EEE"
	fg[PRELIGHT] = "#EEE"
	fg[INSENSITIVE] = "#DDD"

	## text: text color in input widget and treeview
	text[NORMAL] = "#EEE"
	text[SELECTED] = "#EEE"
	text[ACTIVE] = "#EEE"

	## base: background color in input widget and treeview
	base[NORMAL] = "#777"
	base[SELECTED] = "#100"
	base[ACTIVE] = "#112"
}

## The main window is kupfer
widget "kupfer" style "dark"
widget "kupfer.*" style "dark"

## The result list is kupfer-list
widget "kupfer-list.*" style "dark"

## The context menu is GtkWindow.kupfer-menu
## widget "*.kupfer-menu" style "dark"
"""

def cache_filename():
	return os.path.join(config.get_cache_home(), __name__)

def initialize_plugin(name):
	"""
	Theme changes are only reversible if we add
	and remove gtkrc files.
	"""
	filename = cache_filename()
	with open(filename, "wb") as rcfile:
		rcfile.write(DARK_STYLE)
	gtk.rc_add_default_file(filename)
	## force re-read theme
	settings = gtk.settings_get_default()
	gtk.rc_reparse_all_for_settings(settings, True)

def finalize_plugin(name):
	filename = cache_filename()
	gtk.rc_set_default_files([f for f in gtk.rc_get_default_files()
	                          if f != filename])
	## force re-read theme
	settings = gtk.settings_get_default()
	gtk.rc_reparse_all_for_settings(settings, True)
	assert ("kupfer" in filename)
	try:
		os.unlink(filename)
	except OSError:
		pass
