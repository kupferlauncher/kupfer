import gtk
import gobject
import pango

from kupfer import config, plugins, pretty, settings, utils

class PreferencesWindowController (pretty.OutputMixin):
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

		setctl = settings.GetSettingsController()
		entrykeybinding = builder.get_object("entrykeybinding")
		entrykeybinding.set_text(setctl.get_keybinding())
		checkstatusicon = builder.get_object("checkstatusicon")
		checkstatusicon.set_active(setctl.get_show_status_icon())

		columns = [
			{"key": "plugin_id", "type": str },
			{"key": "enabled", "type": bool },
			{"key": "icon-name", "type": str },
			{"key": "markup", "type": str },
		]
		# setup plugin list table
		column_types = [c["type"] for c in columns]
		self.columns = [c["key"] for c in columns]
		self.store = gtk.ListStore(*column_types)
		self.table = gtk.TreeView(self.store)
		self.table.set_headers_visible(False)
		self.table.set_property("enable-search", False)

		checkcell = gtk.CellRendererToggle()
		checkcol = gtk.TreeViewColumn("item", checkcell)
		checkcol.add_attribute(checkcell, "active",
				self.columns.index("enabled"))
		checkcell.connect("toggled", self.on_checkplugin_toggled)

		icon_cell = gtk.CellRendererPixbuf()
		icon_cell.set_property("height", 18)
		icon_cell.set_property("width", 18)
			
		icon_col = gtk.TreeViewColumn("icon", icon_cell)
		icon_col.add_attribute(icon_cell, "icon-name",
				self.columns.index("icon-name"))

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("item", cell)
		col.add_attribute(cell, "markup", self.columns.index("markup"))

		self.table.append_column(checkcol)
		# hide icon for now
		#self.table.append_column(icon_col)
		self.table.append_column(col)

		plugin_info = plugins.get_plugin_info()
		for info in utils.locale_sort(plugin_info,
				key= lambda rec: rec["localized_name"]):
			plugin_id = info["name"]
			if setctl.get_plugin_is_hidden(plugin_id):
				continue
			enabled = setctl.get_plugin_enabled(plugin_id)
			name = info["localized_name"]
			desc = info["description"]
			text = u"<b>%s</b>\n%s" % (name, desc)
			self.store.append((plugin_id, enabled, "kupfer-object", text))
		self.table.show()
		self.pluglist_parent.add(self.table)

	def on_checkstatusicon_toggled(self, widget):
		setctl = settings.GetSettingsController()
		setctl.set_show_status_icon(widget.get_active())
	def on_checkautostart_toggled(self, widget):
		pass
	def on_entrykeybinding_changed(self, widget):
		pass
	def on_closebutton_clicked(self, widget):
		self.hide()
	def on_checkplugin_toggled(self, cell, path):
		it = self.store.get_iter(path)
		id_col = self.columns.index("plugin_id")
		checkcol = self.columns.index("enabled")
		plugin_id = self.store.get_value(it, id_col)
		plugin_is_enabled = not self.store.get_value(it, checkcol)
		self.store.set_value(it, checkcol, plugin_is_enabled)
		setctl = settings.GetSettingsController()
		setctl.set_plugin_enabled(plugin_id, plugin_is_enabled)

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
