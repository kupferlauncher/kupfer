import gtk

from kupfer import config

class PreferencesWindowController (object):
	def __init__(self):
		"""Load ui from data file"""
		builder = gtk.Builder()
		ui_file = config.get_data_file("preferences.ui")
		print ui_file
		if ui_file:
			builder.add_from_file(ui_file)
		else:
			self.window = None
			return
		self.window = builder.get_object("preferenceswindow")
	def show(self):
		self.window.show()
	def hide(self):
		self.window.hide()

_preferences_window = None

def GetPreferencesWindowController():
	global _preferences_window
	if _preferences_window is None:
		_preferences_window = PreferencesWindowController()
	return _preferences_window
