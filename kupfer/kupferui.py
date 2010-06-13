"""
Access functions of Kupfer's Interface
"""
import gtk

from kupfer import utils, version

def show_help():
	"""
	Show Kupfer help pages, if possible
	"""
	if not utils.show_url("ghelp:%s" % version.PACKAGE_NAME):
		utils.show_url(version.WEBSITE)

_about_dialog = None

def show_about_dialog(*ignored, **kwds):
	"""
	create an about dialog and show it
	"""
	# Use only one instance, stored in _about_dialog
	global _about_dialog
	if _about_dialog:
		ab = _about_dialog
	else:
		ab = gtk.AboutDialog()
		ab.set_program_name(version.PROGRAM_NAME)
		ab.set_icon_name(version.ICON_NAME)
		ab.set_logo_icon_name(version.ICON_NAME)
		ab.set_version(version.VERSION)
		ab.set_comments(version.SHORT_DESCRIPTION)
		ab.set_copyright(version.COPYRIGHT)
		ab.set_website(version.WEBSITE)
		ab.set_license(version.LICENSE)
		ab.set_authors(version.AUTHORS)
		if version.DOCUMENTERS:
			ab.set_documenters(version.DOCUMENTERS)
		if version.TRANSLATOR_CREDITS:
			ab.set_translator_credits(version.TRANSLATOR_CREDITS)
		if version.ARTISTS:
			ab.set_artists(version.ARTISTS)

		ab.connect("response", _response_callback)
		# do not delete window on close
		ab.connect("delete-event", lambda *ign: True)
		_about_dialog = ab
	ab.present()

def _response_callback(dialog, response_id):
	dialog.hide()


def show_preferences():
	from kupfer.ui import preferences
	win = preferences.GetPreferencesWindowController()
	win.show()

def show_plugin_info(plugin_id):
	from kupfer.ui import preferences
	prefs = preferences.GetPreferencesWindowController()
	prefs.show_focus_plugin(plugin_id)
