import gtk
import gobject
import pango

from kupfer import config, plugins, pretty, settings, utils
from kupfer import keybindings

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

		self.entrykeybinding = builder.get_object("entrykeybinding")
		self.buttonkeybinding = builder.get_object("buttonkeybinding")
		self.imagekeybindingaux = builder.get_object("imagekeybindingaux")
		self.labelkeybindingaux = builder.get_object("labelkeybindingaux")
		self.buttonpluginabout = builder.get_object("buttonpluginabout")
		self.buttonpluginsettings = builder.get_object("buttonpluginsettings")
		checkstatusicon = builder.get_object("checkstatusicon")

		setctl = settings.GetSettingsController()
		self.entrykeybinding.set_text(setctl.get_keybinding())
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
		self.table.connect("cursor-changed", self.plugin_table_cursor_changed)

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

		self.plugin_info = utils.locale_sort(plugins.get_plugin_info(),
				key= lambda rec: rec["localized_name"])
		for info in self.plugin_info:
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
		self.buttonkeybinding.set_sensitive(True)
		self.imagekeybindingaux.hide()
		self.labelkeybindingaux.hide()
	def on_buttonkeybinding_clicked(self, widget):
		keystr = self.entrykeybinding.get_text()
		self.output_debug("Try set keybinding with", keystr)
		succ = keybindings.bind_key(keystr)
		if succ:
			self.imagekeybindingaux.set_property("stock", gtk.STOCK_APPLY)
			self.labelkeybindingaux.set_text(_("Applied"))
			self.buttonkeybinding.set_sensitive(False)
		else:
			self.imagekeybindingaux.set_property("stock",
					gtk.STOCK_DIALOG_WARNING)
			self.labelkeybindingaux.set_text(_("Keybinding could not be bound"))
		self.imagekeybindingaux.show()
		self.labelkeybindingaux.show()
		if succ:
			setctl = settings.GetSettingsController()
			setctl.set_keybinding(keystr)

	def on_closebutton_clicked(self, widget):
		self.hide()
	def on_checkplugin_toggled(self, cell, path):
		checkcol = self.columns.index("enabled")
		plugin_id = self._id_for_table_path(path)
		it = self.store.get_iter(path)
		plugin_is_enabled = not self.store.get_value(it, checkcol)
		self.store.set_value(it, checkcol, plugin_is_enabled)
		setctl = settings.GetSettingsController()
		setctl.set_plugin_enabled(plugin_id, plugin_is_enabled)

	def _id_for_table_path(self, path):
		it = self.store.get_iter(path)
		id_col = self.columns.index("plugin_id")
		plugin_id = self.store.get_value(it, id_col)
		return plugin_id
	def _plugin_info_for_id(self, plugin_id):
		for info in self.plugin_info:
			if info["name"] == plugin_id:
				return info
		return None

	def plugin_table_cursor_changed(self, table):
		curpath, curcol = table.get_cursor()
		if not curpath:
			self.buttonpluginabout.set_sensitive(False)
			return
		plugin_id = self._id_for_table_path(curpath)
		self.buttonpluginabout.set_sensitive(True)
		sett = plugins.get_plugin_attribute(plugin_id,
				plugins.settings_attribute)
		if sett:
			self.buttonpluginsettings.set_sensitive(True)
		else:
			self.buttonpluginsettings.set_sensitive(False)

	def on_buttonpluginabout_clicked(self, widget):
		curpath, curcol = self.table.get_cursor()
		if not curpath:
			return
		plugin_id = self._id_for_table_path(curpath)
		about = gtk.AboutDialog()
		info = self._plugin_info_for_id(plugin_id)
		about.set_title(info["localized_name"])
		about.set_program_name(info["localized_name"])
		version, description, author = plugins.get_plugin_attributes(plugin_id,
				( "__version__", "__description__", "__author__", ))
		about.set_version(version)
		about.set_comments(description)
		about.set_copyright(author)
		# extra info hack; find the vbox in the about dialog
		child = about.get_child()
		if isinstance(child, gtk.VBox):
			wid = self._make_plugin_info_widget(plugin_id)
			child.pack_start(wid)

		about.show()
		about.connect("response", lambda widget, response: widget.destroy())

	def _make_plugin_info_widget(self, plugin_id):
		version, description, author, sources, actions, text_sources = \
				plugins.get_plugin_attributes(plugin_id, (
				"__version__",
				"__description__",
				"__author__", 
				plugins.sources_attribute,
				plugins.action_decorators_attribute,
				plugins.text_sources_attribute)
				)
		all_items = list()
		vbox = gtk.VBox()
		vbox.set_property("spacing", 5)
		def make_objects_frame(objs, title):
			frame = gtk.Frame()
			frame_label = gtk.Label()
			frame_label.set_markup(u"<b>%s</b>" % title)
			frame.set_property("label-widget", frame_label)
			frame.set_property("shadow-type", gtk.SHADOW_NONE)
			objvbox = gtk.VBox()
			objvbox.set_property("border-width", 3)
			objvbox.set_property("spacing", 3)
			for item in objs:
				plugin_type = plugins.get_plugin_attribute(plugin_id, item)
				if not plugin_type:
					continue
				hbox = gtk.HBox()
				hbox.set_property("spacing", 3)
				obj = plugin_type()
				name = unicode(obj)
				desc = obj.get_description() or u""
				gicon = obj.get_icon()
				im = gtk.Image()
				im.set_property("gicon", gicon)
				im.set_property("pixel-size", 32)
				hbox.pack_start(im, False)
				name_label = u"%s\n<small>%s</small>" % (name, desc)
				label = gtk.Label()
				label.set_markup(name_label)
				hbox.pack_start(label, False)
				objvbox.pack_start(hbox)
			frame.add(objvbox)
			return frame

		sources = list(sources or ()) + list(text_sources or ())
		if sources:
			# TRANS: Plugin contents header
			swid = make_objects_frame(sources, _("Sources"))
			vbox.pack_start(swid)
		if actions:
			# TRANS: Plugin contents header
			awid = make_objects_frame(actions, _("Actions"))
			vbox.pack_start(awid)

		vbox.show_all()
		return vbox
	def on_buttonpluginsettings_clicked(self, widget):
		pass
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
