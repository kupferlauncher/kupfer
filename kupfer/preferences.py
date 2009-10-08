import gtk
import gio
import gobject
import pango

from xdg import BaseDirectory as base
from xdg import DesktopEntry as desktop
import os

from kupfer import config, plugins, pretty, settings, utils, icons
from kupfer import keybindings

class PreferencesWindowController (pretty.OutputMixin):
	def __init__(self):
		"""Load ui from data file"""
		builder = gtk.Builder()
		ui_file = config.get_data_file("preferences.ui")
		try:
			import version_subst
		except ImportError:
			package_name = "kupfer"
		else:
			package_name = version_subst.PACKAGE_NAME
		builder.set_translation_domain(package_name)

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
		self.dirlist_parent = builder.get_object("directory_list_parent")
		self.plugin_about_parent = builder.get_object("plugin_about_parent")

		self.entrykeybinding = builder.get_object("entrykeybinding")
		self.buttonkeybinding = builder.get_object("buttonkeybinding")
		self.imagekeybindingaux = builder.get_object("imagekeybindingaux")
		self.labelkeybindingaux = builder.get_object("labelkeybindingaux")
		self.buttonremovedirectory = builder.get_object("buttonremovedirectory")
		checkautostart = builder.get_object("checkautostart")
		checkstatusicon = builder.get_object("checkstatusicon")

		setctl = settings.GetSettingsController()
		self.entrykeybinding.set_text(setctl.get_keybinding())
		checkautostart.set_active(self._get_should_autostart())
		checkstatusicon.set_active(setctl.get_show_status_icon())

		# Plugin List
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
		self.table.set_rules_hint(True)
		self.table.connect("cursor-changed", self.plugin_table_cursor_changed)
		self.table.get_selection().set_mode(gtk.SELECTION_BROWSE)

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
			text = u"%s" % name
			self.store.append((plugin_id, enabled, "kupfer-object", text))
		self.table.show()
		self.pluglist_parent.add(self.table)

		# Directory List
		self.dir_store = gtk.ListStore(str, gio.Icon, str)
		self.dir_table = gtk.TreeView(self.dir_store)
		self.dir_table.set_headers_visible(False)
		self.dir_table.set_property("enable-search", False)
		self.dir_table.connect("cursor-changed", self.dir_table_cursor_changed)
		self.dir_table.get_selection().set_mode(gtk.SELECTION_BROWSE)

		icon_cell = gtk.CellRendererPixbuf()
			
		icon_col = gtk.TreeViewColumn("icon", icon_cell)
		icon_col.add_attribute(icon_cell, "gicon", 1)

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("name", cell)
		col.add_attribute(cell, "text", 2)
		cell.set_property("ellipsize", pango.ELLIPSIZE_END)
		self.dir_table.append_column(icon_col)
		self.dir_table.append_column(col)
		self.dir_table.show()
		self.dirlist_parent.add(self.dir_table)
		self.read_directory_settings()

	def read_directory_settings(self):
		setctl = settings.GetSettingsController()
		dirs = setctl.get_directories()
		for d in dirs:
			self.add_directory_model(d, store=False)

	def add_directory_model(self, d, store=False):
		have = list(os.path.normpath(row[0]) for row in self.dir_store)
		if d in have:
			self.output_debug("Ignoring duplicate directory: ", d)
			return
		else:
			have.append(d)

		d = os.path.expanduser(d)
		dispname = utils.get_display_path_for_bytestring(d)
		gicon = icons.get_gicon_for_file(d)
		self.dir_store.append((d, gicon, dispname))

		if store:
			setctl = settings.GetSettingsController()
			setctl.set_directories(have)

	def remove_directory_model(self, rowiter, store=True):
		dirpath = self.dir_store.get_value(rowiter, 0)
		self.dir_store.remove(rowiter)
		if store:
			have = list(os.path.normpath(row[0]) for row in self.dir_store)
			setctl = settings.GetSettingsController()
			setctl.set_directories(have)

	def on_preferenceswindow_key_press_event(self, widget, event):
		if event.keyval == gtk.gdk.keyval_from_name("Escape"):
			self.hide()
			return True

	def on_checkstatusicon_toggled(self, widget):
		setctl = settings.GetSettingsController()
		setctl.set_show_status_icon(widget.get_active())

	def _get_should_autostart(self):
		KUPFER_DESKTOP = "kupfer.desktop"
		AUTOSTART_KEY = "X-GNOME-Autostart-enabled"
		autostart_dir = base.save_config_path("autostart")
		autostart_file = os.path.join(autostart_dir, KUPFER_DESKTOP)
		if not os.path.exists(autostart_file):
			return False
		dfile = desktop.DesktopEntry(autostart_file)
		return (dfile.hasKey(AUTOSTART_KEY) and
				dfile.get(AUTOSTART_KEY, type="boolean"))

	def on_checkautostart_toggled(self, widget):
		KUPFER_DESKTOP = "kupfer.desktop"
		AUTOSTART_KEY = "X-GNOME-Autostart-enabled"
		autostart_dir = base.save_config_path("autostart")
		autostart_file = os.path.join(autostart_dir, KUPFER_DESKTOP)
		if not os.path.exists(autostart_file):
			desktop_files = list(base.load_data_paths("applications",
				KUPFER_DESKTOP))
			if not desktop_files:
				self.output_error("Installed kupfer desktop file not found!")
				return
			desktop_file_path = desktop_files[0]
			# Read installed file and modify it
			dfile = desktop.DesktopEntry(desktop_file_path)
			executable = dfile.getExec()
			if "--no-splash" not in executable:
				executable += " --no-splash"
				dfile.set("Exec", executable)
		else:
			dfile = desktop.DesktopEntry(autostart_file)
		activestr = str(bool(widget.get_active())).lower()
		self.output_debug("Setting autostart to", activestr)
		dfile.set(AUTOSTART_KEY, activestr)
		dfile.write(filename=autostart_file)

	def on_entrykeybinding_changed(self, widget):
		sensitive = widget.get_text() != keybindings.get_currently_bound_key()
		self.buttonkeybinding.set_sensitive(sensitive)
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

	def on_helpbutton_clicked(self, widget):
		pass
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
			return
		plugin_id = self._id_for_table_path(curpath)
		self.plugin_sidebar_update(plugin_id)

	def plugin_sidebar_update(self, plugin_id):
		about = gtk.VBox()
		about.set_property("spacing", 15)
		about.set_property("border-width", 5)
		info = self._plugin_info_for_id(plugin_id)
		title_label = gtk.Label()
		title_label.set_markup(u"<b><big>%s</big></b>" % info["localized_name"])
		version, description, author = plugins.get_plugin_attributes(plugin_id,
				( "__version__", "__description__", "__author__", ))
		about.pack_start(title_label, False)
		infobox = gtk.VBox()
		infobox.set_property("spacing", 3)
		# TRANS: Plugin info fields
		for field, val in zip((_("Description"), _("Author")),
				(description, author)):
			if not val:
				continue
			label = gtk.Label()
			label.set_alignment(0, 0)
			label.set_markup(u"<b>%s</b>" % field)
			infobox.pack_start(label, False)
			label = gtk.Label()
			label.set_alignment(0, 0)
			label.set_markup(u"%s" % gobject.markup_escape_text(val))
			label.set_line_wrap(True)
			infobox.pack_start(label, False)
		if version:
			label = gtk.Label()
			label.set_alignment(0, 0)
			label.set_markup(u"<b>%s:</b> %s" % (_("Version"), version))
			infobox.pack_start(label, False)
		about.pack_start(infobox, False)

		# Check for plugin load error
		error = plugins.get_plugin_error(plugin_id)
		if error:
			label = gtk.Label()
			label.set_alignment(0, 0)
			label.set_markup(u"<b>%s</b>\n%s" %
					(_("Plugin could not be read due to an error:"), error))
			about.pack_start(label, False)

		wid = self._make_plugin_info_widget(plugin_id)
		about.pack_start(wid, False)
		psettings_wid = self._make_plugin_settings_widget(plugin_id)
		if psettings_wid:
			about.pack_start(psettings_wid, False)

		oldch = self.plugin_about_parent.get_child()
		if oldch:
			self.plugin_about_parent.remove(oldch)
		vp = gtk.Viewport()
		vp.set_shadow_type(gtk.SHADOW_NONE)
		vp.add(about)
		self.plugin_about_parent.add(vp)
		self.plugin_about_parent.show_all()

	def _make_plugin_info_widget(self, plugin_id):
		sources, actions, text_sources = \
				plugins.get_plugin_attributes(plugin_id, (
				plugins.sources_attribute,
				plugins.action_decorators_attribute,
				plugins.text_sources_attribute)
				)
		all_items = list()
		vbox = gtk.VBox()
		vbox.set_property("spacing", 5)
		def make_objects_frame(objs, title):
			frame_label = gtk.Label()
			frame_label.set_markup(u"<b>%s</b>" % title)
			frame_label.set_alignment(0, 0)
			objvbox = gtk.VBox()
			objvbox.pack_start(frame_label, False)
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
				name_label = \
					u"%s\n<small>%s</small>" % (name, desc) if desc else \
					u"%s" % (name, )
				label = gtk.Label()
				label.set_markup(name_label)
				hbox.pack_start(label, False)
				objvbox.pack_start(hbox)
			return objvbox

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

	def _get_plugin_change_callback(self, plugin_id, key, value_type,
			get_attr, no_false_values=False):
		"""Callback factory for the plugin parameter configuration"""
		def callback(widget):
			value = getattr(widget, get_attr)()
			if no_false_values and not value:
				return
			setctl = settings.GetSettingsController()
			setctl.set_plugin_config(plugin_id, key, value, value_type)
		return callback

	def _make_plugin_settings_widget(self, plugin_id):
		plugin_settings = plugins.get_plugin_attribute(plugin_id,
				plugins.settings_attribute)
		if not plugin_settings:
			return None

		info = self._plugin_info_for_id(plugin_id)
		title_label = gtk.Label()
		# TRANS: Plugin-specific configuration (header)
		title_label.set_markup(u"<b>%s</b>" % _("Configuration"))
		title_label.set_alignment(0, 0)

		vbox = gtk.VBox()
		vbox.pack_start(title_label, False)
		#vbox.set_property("spacing", 5)

		plugin_settings_keys = iter(plugin_settings) if plugin_settings else ()
		for setting in plugin_settings_keys:
			typ = plugin_settings.get_value_type(setting)
			alternatives = plugin_settings.get_alternatives(setting)
			tooltip = plugin_settings.get_tooltip(setting)
			wid = None
			hbox = gtk.HBox()
			hbox.set_property("spacing", 10)
			if tooltip:
				hbox.set_tooltip_text(tooltip)
			label = plugin_settings.get_label(setting)
			label_wid = gtk.Label(label)
			if issubclass(typ, basestring):
				if alternatives:
					wid = gtk.combo_box_new_text()
					val = plugin_settings[setting]
					active_index = -1
					for idx, text in enumerate(alternatives):
						wid.append_text(text)
						if text == val:
							active_index = idx
					if active_index < 0:
						wid.prepend_text(val)
						active_index = 0
					wid.set_active(active_index)
					wid.connect("changed", self._get_plugin_change_callback(
						plugin_id, setting, typ, "get_active_text"))
				else:
					wid = gtk.Entry()
					wid.set_text(plugin_settings[setting])
					wid.connect("changed", self._get_plugin_change_callback(
						plugin_id, setting, typ, "get_text",
						no_false_values=True))
				hbox.pack_start(label_wid, False)
				hbox.pack_start(wid, True)

			elif issubclass(typ, bool):
				wid = gtk.CheckButton(label)
				wid.set_active(plugin_settings[setting])
				hbox.pack_start(wid, False)
				wid.connect("toggled", self._get_plugin_change_callback(
					plugin_id, setting, typ, "get_active"))
			elif issubclass(typ, int):
				wid = gtk.SpinButton()
				wid.set_increments(1, 1)
				wid.set_range(0, 1000)
				wid.set_value(plugin_settings[setting])
				hbox.pack_start(label_wid, False, True)
				hbox.pack_start(wid, False)
				wid.connect("changed", self._get_plugin_change_callback(
					plugin_id, setting, typ, "get_text", no_false_values=True))
			vbox.pack_start(hbox, False)

		vbox.show_all()
		return vbox

	def on_buttonadddirectory_clicked(self, widget):
		# TRANS: File Chooser Title
		chooser_dialog = gtk.FileChooserDialog(title=_("Choose a Directory"),
				action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
				buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
					gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		if chooser_dialog.run() == gtk.RESPONSE_ACCEPT:
			selected_dir = chooser_dialog.get_filename()
			self.add_directory_model(selected_dir, store=True)
		chooser_dialog.hide()

	def on_buttonremovedirectory_clicked(self, widget):
		curpath, curcol = self.dir_table.get_cursor()
		if not curpath:
			return
		it = self.dir_store.get_iter(curpath)
		self.remove_directory_model(it, store=True)

	def dir_table_cursor_changed(self, table):
		curpath, curcol = table.get_cursor()
		if not curpath or not self.dir_store:
			self.buttonremovedirectory.set_sensitive(False)
			return
		self.buttonremovedirectory.set_sensitive(True)

	def show(self):
		self.window.present()
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
