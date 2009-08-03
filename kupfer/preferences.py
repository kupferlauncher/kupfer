import gtk
import gobject
import pango

from kupfer import config, plugins, pretty, settings

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
		builder.connect_signals(self)
		self.window = builder.get_object("preferenceswindow")
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.connect("delete-event", self._close_window)
		self.pluglist_parent = builder.get_object("plugin_list_parent")
		# setup plugin list table
		columns = (bool, str, str)
		self.store = gtk.ListStore(str, *columns)
		self.table = gtk.TreeView(self.store)
		self.table.set_headers_visible(False)
		self.table.set_property("enable-search", False)

		checkcell = gtk.CellRendererToggle()
		checkcol = gtk.TreeViewColumn("item", checkcell)
		checkcol.add_attribute(checkcell, "active", 1)
		checkcell.connect("toggled", self.on_checkplugin_toggled)

		icon_cell = gtk.CellRendererPixbuf()
		icon_cell.set_property("height", 18)
		icon_cell.set_property("width", 18)
			
		icon_col = gtk.TreeViewColumn("icon", icon_cell)
		icon_col.add_attribute(icon_cell, "icon-name", 2)

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("item", cell)
		col.add_attribute(cell, "markup", 3)

		self.table.append_column(checkcol)
		# hide icon for now
		#self.table.append_column(icon_col)
		self.table.append_column(col)

		setctl = settings.GetSettingsController()

		for info in plugins.get_plugin_info():
			plugin_id = info["name"]
			name = info["localized_name"]
			enabled = setctl.get_plugin_enabled(plugin_id)
			desc = info["description"]
			text = u"<b>%s</b>\n%s" % (name, desc)
			self.store.append((plugin_id, enabled, "kupfer-object", text))
		self.table.show()
		self.pluglist_parent.add(self.table)

	def on_checkstatusicon_toggled(self, widget):
		pass
	def on_checkautostart_toggled(self, widget):
		pass
	def on_entrykeybinding_changed(self, widget):
		pass
	def on_closebutton_clicked(self, widget):
		self.hide()
	def on_checkplugin_toggled(self, cell, path):
		print "Toggled", cell, path
	def show(self):
		self.window.show()
	def hide(self):
		self.window.hide()
	def _close_window(self, *ignored):
		self.hide()
		return True

_preferences_window = None

def GetPreferencesWindowController():
	global _preferences_window
	if _preferences_window is None:
		_preferences_window = PreferencesWindowController()
	return _preferences_window
