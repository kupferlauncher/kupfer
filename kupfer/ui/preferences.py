import os
import re

import gtk
import gio
import gobject
import pango
from xdg import BaseDirectory as base
from xdg import DesktopEntry as desktop


from kupfer import config, pretty, utils, icons, version
from kupfer import scheduler, kupferstring
from kupfer.core import settings, plugins, relevance
from kupfer.ui import keybindings
from kupfer.ui.credentials_dialog import ask_user_credentials
from kupfer.ui import getkey_dialog

# A major HACK
# http://tadeboro.blogspot.com/2009/05/wrapping-adn-resizing-gtklabel.html
def _cb_allocate(label, allocation):
	label.set_size_request(allocation.width, -1)

def wrapped_label(text=None):
	label = gtk.Label(text)
	label.set_line_wrap(True)
	label.connect("size-allocate", _cb_allocate)
	return label

class PreferencesWindowController (pretty.OutputMixin):

	KEYBINDING_NAMES = {
		'keybinding': _("Show Main Interface"),
		'magickeybinding': _("Show with Selection"),
	}

	KEYBINDING_TARGETS = {
		"keybinding": keybindings.KEYBINDING_DEFAULT,
		"magickeybinding": keybindings.KEYBINDING_MAGIC,
	}

	ACCELERATOR_NAMES = {
		'activate': _('Alternate Activate'),
		'comma_trick': _('Comma Trick'),
		'compose_action': _('Compose Command'),
		'reset_all': _('Reset All'),
		'select_quit': _('Select Quit'),
		'select_selected_file': _('Select Selected File'),
		'select_selected_text': _('Select Selected Text'),
		'show_help': _('Show Help'),
		'switch_to_source': _('Switch to First Pane'),
		"toggle_text_mode_quick": _('Toggle Text Mode'),
	}

	def __init__(self):
		"""Load ui from data file"""
		builder = gtk.Builder()
		builder.set_translation_domain(version.PACKAGE_NAME)
		ui_file = config.get_data_file("preferences.ui")

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
		self.preferences_notebook = builder.get_object("preferences_notebook")

		self.buttonremovedirectory = builder.get_object("buttonremovedirectory")
		checkautostart = builder.get_object("checkautostart")
		checkstatusicon = builder.get_object("checkstatusicon")
		checkusecommandkeys = builder.get_object("checkusecommandkeys")
		self.entry_plugins_filter = builder.get_object('entry_plugins_filter')
		self.keybindings_list_parent = builder.get_object('keybindings_list_parent')
		self.gkeybindings_list_parent = builder.get_object('gkeybindings_list_parent')

		setctl = settings.GetSettingsController()
		checkautostart.set_active(self._get_should_autostart())
		checkstatusicon.set_active(setctl.get_show_status_icon())
		checkusecommandkeys.set_active(setctl.get_use_command_keys())

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

		self.plugin_list_timer = scheduler.Timer()
		self.plugin_info = utils.locale_sort(plugins.get_plugin_info(),
				key= lambda rec: rec["localized_name"])
		self._refresh_plugin_list()
		self.output_debug("Standard Plugins: %d" % len(self.store))
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

		# keybindings list
		self.keybind_table, self.keybind_store = _create_conf_keys_list()
		self.keybindings_list_parent.add(self.keybind_table)
		self.keybind_table.connect("row-activated", self.on_keybindings_row_activate)
		# global keybindings list
		self.gkeybind_table, self.gkeybind_store = _create_conf_keys_list()
		self.gkeybindings_list_parent.add(self.gkeybind_table)
		self.gkeybind_table.connect("row-activated",
				self.on_gkeybindings_row_activate)

		self._show_keybindings(setctl)
		self._show_gkeybindings(setctl)

	def _show_keybindings(self, setctl):
		names = self.KEYBINDING_NAMES
		self.keybind_store.clear()
		for binding in sorted(names, key=lambda k: names[k]):
			accel = setctl.get_global_keybinding(binding)
			label = gtk.accelerator_get_label(*gtk.accelerator_parse(accel))
			self.keybind_store.append((names[binding], label, binding))

	def _show_gkeybindings(self, setctl):
		names = self.ACCELERATOR_NAMES
		self.gkeybind_store.clear()
		for binding in sorted(names, key=lambda k: names[k]):
			accel = setctl.get_accelerator(binding)
			label = gtk.accelerator_get_label(*gtk.accelerator_parse(accel))
			self.gkeybind_store.append((names[binding], label, binding))

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
		pass

	def on_buttonkeybinding_clicked(self, widget):
		keystr = getkey_dialog.ask_for_key(keybindings.bind_key)
		if keystr:
			self.entrykeybinding.set_text(keystr)
			self.output_debug("Try set keybinding with", keystr)
			succ = keybindings.bind_key(keystr)
			setctl = settings.GetSettingsController()
			setctl.set_keybinding(keystr)

	def on_helpbutton_clicked(self, widget):
		pass
	def on_closebutton_clicked(self, widget):
		self.hide()

	def _refresh_plugin_list(self, us_filter=None):
		"List plugins that pass text filter @us_filter or list all if None"
		self.store.clear()
		setctl = settings.GetSettingsController()

		if us_filter:
			self.plugin_list_timer.set_ms(300, self._show_focus_topmost_plugin)
		else:
			self.plugin_list_timer.invalidate()

		for info in self.plugin_info:
			plugin_id = info["name"]
			if setctl.get_plugin_is_hidden(plugin_id):
				continue
			enabled = setctl.get_plugin_enabled(plugin_id)
			name = info["localized_name"]
			folded_name = kupferstring.tofolded(name)
			desc = info["description"]
			text = u"%s" % name

			if us_filter:
				name_score = relevance.score(name, us_filter)
				fold_name_score = relevance.score(folded_name, us_filter)
				desc_score = relevance.score(desc, us_filter)
				if not name_score and not fold_name_score and desc_score < 0.9:
					continue

			self.store.append((plugin_id, enabled, "kupfer-object", text))

	def _show_focus_topmost_plugin(self):
		try:
			first_row = iter(self.store).next()
		except StopIteration:
			return
		plugin_id = first_row[0]
		self.show_focus_plugin(plugin_id)

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

	def _table_path_for_id(self, id_):
		"""
		Find the tree path of plugin @id_
		"""
		id_col = self.columns.index("plugin_id")
		for row in self.store:
			plugin_id = row[id_col]
			if plugin_id == id_:
				return row.path
		raise ValueError("No such plugin %s" % id_)


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
			label = wrapped_label()
			label.set_alignment(0, 0)
			label.set_markup(u"%s" % gobject.markup_escape_text(val))
			label.set_selectable(True)
			infobox.pack_start(label, False)
		if version:
			label = wrapped_label()
			label.set_alignment(0, 0)
			label.set_markup(u"<b>%s:</b> %s" % (_("Version"), version))
			label.set_selectable(True)
			infobox.pack_start(label, False)
		about.pack_start(infobox, False)

		# Check for plugin load exception
		exc_info = plugins.get_plugin_error(plugin_id)
		if exc_info is not None:
			etype, error, tb = exc_info
			# TRANS: Error message when Plugin needs a Python module to load
			import_error_localized = _("Python module '%s' is needed") % u"\\1"
			import_error_pat = u"No module named ([^\s]+)"
			errmsg = unicode(error)
			if re.match(import_error_pat, errmsg):
				errstr = re.sub(import_error_pat,
						import_error_localized,
						errmsg, count=1)
			else:
				import traceback
				errstr = "".join(traceback.format_exception(*exc_info))

			label = wrapped_label()
			label.set_alignment(0, 0)
			label.set_markup(u"<b>%s</b>\n\n%s" % (
				_("Plugin could not be read due to an error:"),
				gobject.markup_escape_text(errstr),
				))
			label.set_selectable(True)
			about.pack_start(label, False)
		elif not plugins.is_plugin_loaded(plugin_id):
			label = gtk.Label()
			label.set_alignment(0, 0)
			label.set_text(u"(%s)" % _("disabled"))
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
				label = wrapped_label()
				label.set_markup(name_label)
				hbox.pack_start(label, False)
				objvbox.pack_start(hbox)
				# Display information for application content-sources.
				try:
					leaf_repr = obj.get_leaf_repr()
				except AttributeError:
					continue
				if leaf_repr is None:
					continue
				if hasattr(leaf_repr, "is_valid") and not leaf_repr.is_valid():
					continue
				hbox = gtk.HBox()
				hbox.set_property("spacing", 3)
				gicon = leaf_repr.get_icon()
				im = gtk.Image()
				im.set_property("gicon", gicon)
				im.set_property("pixel-size", 16)
				hbox.pack_start(gtk.Label(_("Content of")), False)
				hbox.pack_start(im, False)
				hbox.pack_start(gtk.Label(unicode(leaf_repr)), False)
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

	def _get_plugin_credentials_callback(self, plugin_id, key):
		def callback(widget):
			setctl = settings.GetSettingsController()
			val_type = settings.UserNamePassword
			upass = setctl.get_plugin_config(plugin_id, key, val_type) \
					or settings.UserNamePassword()
			user_password = ask_user_credentials(upass.username, upass.password)
			if user_password:
				upass.username, upass.password = user_password
				setctl.set_plugin_config(plugin_id, key, upass, val_type)
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

			if issubclass(typ, settings.UserNamePassword):
				wid = gtk.Button(label or _("Set username and password"))
				wid.connect("clicked", self._get_plugin_credentials_callback(
						plugin_id, setting))
				hbox.pack_start(wid, False)
				vbox.pack_start(hbox, False)
				continue

			label_wid = wrapped_label(label)
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

	def on_entry_plugins_filter_changed(self, widget):
		s_filter = widget.get_text()
		us_filter = kupferstring.tounicode(s_filter).lower()
		self._refresh_plugin_list(us_filter)

	def on_entry_plugins_filter_icon_press(self, entry, icon_pos, event):
		entry.set_text('')

	def on_keybindings_row_activate(self, treeview, path, view_column):
		def bind_key_func(target):
			def bind_key(keystr):
				return keybindings.bind_key(keystr, target)
			return bind_key

		it = self.keybind_store.get_iter(path)
		keybind_id = self.keybind_store.get_value(it, 2)
		setctl = settings.GetSettingsController()
		curr_key = setctl.get_global_keybinding(keybind_id)
		bind_func = bind_key_func(self.KEYBINDING_TARGETS[keybind_id])
		keystr = getkey_dialog.ask_for_key(bind_func, curr_key)
		if keystr == '':
			keybindings.bind_key(None, self.KEYBINDING_TARGETS[keybind_id])
			self.keybind_store.set_value(it, 1, '')
		elif self._is_good_keystr(keystr):
			setctl.set_global_keybinding(keybind_id, keystr)
			label = gtk.accelerator_get_label(*gtk.accelerator_parse(keystr))
			self.keybind_store.set_value(it, 1, label)

	def _is_good_keystr(self, keystr):
		# Reject single letters so you can't bind 'A' etc
		if keystr is None:
			return False
		ukeystr = kupferstring.tounicode(keystr)
		return not (len(ukeystr) == 1 and ukeystr.isalnum())

	def on_gkeybindings_row_activate(self, treeview, path, view_column):
		it = self.gkeybind_store.get_iter(path)
		keybind_id = self.gkeybind_store.get_value(it, 2)
		setctl = settings.GetSettingsController()
		curr_key = setctl.get_accelerator(keybind_id)
		keystr = getkey_dialog.ask_for_key(previous_key=curr_key)
		if self._is_good_keystr(keystr):
			setctl.set_accelerator(keybind_id, keystr)
			label = gtk.accelerator_get_label(*gtk.accelerator_parse(keystr))
			self.gkeybind_store.set_value(it, 1, label)

	def on_button_reset_keys_clicked(self, button):
		if self.ask_user_for_reset_keybinding():
			setctl = settings.GetSettingsController()
			setctl.reset_keybindings()
			self._show_keybindings(setctl)
			# Unbind all before re-binding
			for keybind_id, target in self.KEYBINDING_TARGETS.iteritems():
				keybindings.bind_key(None, target)
			for keybind_id, target in self.KEYBINDING_TARGETS.iteritems():
				keystr = setctl.get_global_keybinding(keybind_id)
				keybindings.bind_key(keystr, target)

	def on_button_reset_gkeys_clicked(self, button):
		if self.ask_user_for_reset_keybinding():
			setctl = settings.GetSettingsController()
			setctl.reset_accelerators()
			self._show_gkeybindings(setctl)

	def on_checkusecommandkeys_toggled(self, widget):
		setctl = settings.GetSettingsController()
		setctl.set_use_command_keys(widget.get_active())

	def dir_table_cursor_changed(self, table):
		curpath, curcol = table.get_cursor()
		if not curpath or not self.dir_store:
			self.buttonremovedirectory.set_sensitive(False)
			return
		self.buttonremovedirectory.set_sensitive(True)

	def show(self):
		self.window.present()
	def show_focus_plugin(self, plugin_id):
		"""
		Open and show information about plugin @plugin_id
		"""
		try:
			table_path = self._table_path_for_id(plugin_id)
		except ValueError:
			self.entry_plugins_filter.set_text(u"")
			self._refresh_plugin_list()
			table_path = self._table_path_for_id(plugin_id)
		self.table.set_cursor(table_path)
		self.table.scroll_to_cell(table_path)
		# FIXME: Revisit if we add new pages to the GtkNotebook
		self.preferences_notebook.next_page()
		self.preferences_notebook.next_page()
		self.window.present()

	def hide(self):
		self.window.hide()
	def _close_window(self, *ignored):
		self.hide()
		return True

	def ask_user_for_reset_keybinding(self):
		dlg = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION)
		dlg.set_markup(_("Reset all shortcuts to default values?"))
		dlg.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CLOSE,
				_('Reset'), gtk.RESPONSE_ACCEPT)
		result = dlg.run() == gtk.RESPONSE_ACCEPT
		dlg.destroy()
		return result


_conf_keys_list_columns = [{"key": "name", "type":str, 'header': _('Command')},
		{"key": "key", "type": str, 'header': _('Shortcut') },
		{"key": "keybinding_id", "type": str, 'header':  None}]
_conf_keys_list_column_types = [c["type"] for c in _conf_keys_list_columns]

def _create_conf_keys_list():
	keybind_store = gtk.ListStore(*_conf_keys_list_column_types)
	keybind_table = gtk.TreeView(keybind_store)
	for idx, col in enumerate(_conf_keys_list_columns):
		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn(col['header'], renderer, text=idx)
		column.set_visible(col['header'] is not None)
		keybind_table.append_column(column)
	keybind_table.set_property("enable-search", False)
	keybind_table.set_rules_hint(True)
	keybind_table.set_headers_visible(True)
	keybind_table.show()
	return keybind_table, keybind_store


_preferences_window = None

def GetPreferencesWindowController():
	global _preferences_window
	if _preferences_window is None:
		_preferences_window = PreferencesWindowController()
	return _preferences_window
