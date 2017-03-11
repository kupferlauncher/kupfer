import os
import re

import gi

from gi.repository import GLib, GObject, Gtk, Gio, Gdk
from gi.repository import Pango
from xdg import BaseDirectory as base
from xdg import DesktopEntry as desktop
from xdg import Exceptions as xdg_e


from kupfer import config, pretty, utils, icons, version
from kupfer import scheduler, kupferstring
from kupfer import kupferui
from kupfer.core import settings, plugins, relevance, sources
from kupfer.ui import keybindings
from kupfer.ui.credentials_dialog import ask_user_credentials
from kupfer.ui import getkey_dialog
from kupfer.ui import accelerators
from kupfer import plugin_support

# index in GtkNotebook
PLUGIN_LIST_PAGE = 2

# List icon pixel size
LIST_ICON_SIZE = 18

# A major HACK
# http://tadeboro.blogspot.com/2009/05/wrapping-adn-resizing-gtklabel.html
def _cb_allocate(label, allocation, maxwid):
    if maxwid == -1:
        maxwid = 300
    label.set_size_request(min(maxwid, allocation.width), -1)
    pass

def wrapped_label(text=None, maxwid=-1):
    label = Gtk.Label.new(text)
    label.set_line_wrap(True)
    label.connect("size-allocate", _cb_allocate, maxwid)
    return label

def kobject_should_show(obj):
    try:
        leaf_repr = obj.get_leaf_repr()
    except AttributeError:
        pass
    else:
        if leaf_repr is None:
            return True
        if hasattr(leaf_repr, "is_valid") and not leaf_repr.is_valid():
            return False
    return True

def set_combobox(value, combobox):
    """
    Set activate the alternative in the combobox with text value
    """
    value = str(value)
    col = combobox.get_entry_text_column()
    combobox_store = combobox.get_model()
    for row in combobox.get_model():
        if row[col] == value:
            combobox.set_active_iter(row.iter)
            return


class PreferencesWindowController (pretty.OutputMixin):

    KEYBINDING_NAMES = {
        # TRANS: Names of global keyboard shortcuts
        'keybinding': _("Show Main Interface"),
        'magickeybinding': _("Show with Selection"),
    }

    KEYBINDING_TARGETS = {
        "keybinding": keybindings.KEYBINDING_DEFAULT,
        "magickeybinding": keybindings.KEYBINDING_MAGIC,
    }


    def __init__(self):
        """Load ui from data file"""
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)
        ui_file = config.get_data_file("preferences.ui")

        if ui_file:
            builder.add_from_file(ui_file)
        else:
            self.window = None
            return
        self.window = builder.get_object("preferenceswindow")
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("delete-event", self._close_window)
        self.pluglist_parent = builder.get_object("plugin_list_parent")
        self.dirlist_parent = builder.get_object("directory_list_parent")
        self.plugin_about_parent = builder.get_object("plugin_about_parent")
        self.preferences_notebook = builder.get_object("preferences_notebook")

        self.buttonremovedirectory = builder.get_object("buttonremovedirectory")
        checkautostart = builder.get_object("checkautostart")
        checkstatusicon_gtk = builder.get_object("checkstatusicon_gtk")
        checkstatusicon_ai = builder.get_object("checkstatusicon_ai")
        combo_icons_large_size = builder.get_object("icons_large_size")
        combo_icons_small_size = builder.get_object("icons_small_size")
        checkusecommandkeys = builder.get_object("checkusecommandkeys")
        radio_actionaccelalt = builder.get_object("radio_actionaccelalt")
        radio_actionaccelctrl = builder.get_object("radio_actionaccelctrl")
        self.entry_plugins_filter = builder.get_object('entry_plugins_filter')
        self.keybindings_list_parent = builder.get_object('keybindings_list_parent')
        self.gkeybindings_list_parent = builder.get_object('gkeybindings_list_parent')
        source_list_parent = builder.get_object("source_list_parent")
        button_reset_keys = builder.get_object("button_reset_keys")
        self.sources_list_ctrl = SourceListController(source_list_parent)

        setctl = settings.GetSettingsController()
        checkautostart.set_active(self._get_should_autostart())
        checkstatusicon_gtk.set_active(setctl.get_show_status_icon())

        large_icon_size = setctl.get_config_int("Appearance", "icon_large_size")
        small_icon_size = setctl.get_config_int("Appearance", "icon_small_size")

        set_combobox(large_icon_size, combo_icons_large_size)
        set_combobox(small_icon_size, combo_icons_small_size)

        if supports_app_indicator():
            checkstatusicon_ai.set_active(setctl.get_show_status_icon_ai())
        else:
            checkstatusicon_ai.set_sensitive(False)

        label = checkstatusicon_gtk.get_label()
        checkstatusicon_gtk.set_label(label + " (GtkStatusIcon)")
        label = checkstatusicon_ai.get_label()
        checkstatusicon_ai.set_label(label + " (AppIndicator)")


        checkusecommandkeys.set_active(setctl.get_use_command_keys())
        radio_actionaccelalt.set_active(setctl.get_action_accelerator_modifer() != 'ctrl')
        radio_actionaccelctrl.set_active(setctl.get_action_accelerator_modifer() == 'ctrl')

        # List store with columns (Name, ID) 
        # Make alternative comboboxes
        terminal_combobox = builder.get_object("terminal_combobox")
        icons_combobox = builder.get_object("icons_combobox")

        def make_combobox_model(combobox):
            combobox_store = Gtk.ListStore(GObject.TYPE_STRING,
                                           GObject.TYPE_STRING)
            combobox.set_model(combobox_store)
            combobox_cell = Gtk.CellRendererText()
            combobox.pack_start(combobox_cell, True)
            combobox.add_attribute(combobox_cell, 'text', 0)

        make_combobox_model(terminal_combobox)
        make_combobox_model(icons_combobox)

        self._update_alternative_combobox('terminal', terminal_combobox)
        self._update_alternative_combobox('icon_renderer', icons_combobox)
        self.terminal_combobox = terminal_combobox
        self.icons_combobox = icons_combobox
        setctl.connect("alternatives-changed", self._on_alternatives_changed)


        # Plugin List
        columns = [
            {"key": "plugin_id", "type": str },
            {"key": "enabled", "type": bool },
            {"key": "icon-name", "type": str },
            {"key": "text", "type": str },
        ]
        # setup plugin list table
        column_types = [c["type"] for c in columns]
        self.columns = [c["key"] for c in columns]
        self.store = Gtk.ListStore.new(column_types)
        self.table = Gtk.TreeView.new_with_model(self.store)
        self.table.set_headers_visible(False)
        self.table.set_property("enable-search", False)
        self.table.connect("cursor-changed", self.plugin_table_cursor_changed)
        self.table.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        checkcell = Gtk.CellRendererToggle()
        checkcol = Gtk.TreeViewColumn("item", checkcell)
        checkcol.add_attribute(checkcell, "active",
                self.columns.index("enabled"))
        checkcell.connect("toggled", self.on_checkplugin_toggled)

        icon_cell = Gtk.CellRendererPixbuf()
        icon_cell.set_property("height", LIST_ICON_SIZE)
        icon_cell.set_property("width", LIST_ICON_SIZE)

        icon_col = Gtk.TreeViewColumn("icon", icon_cell)
        icon_col.add_attribute(icon_cell, "icon-name",
                self.columns.index("icon-name"))

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("item", cell)
        col.add_attribute(cell, "text", self.columns.index("text"))

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
        self.dir_store = Gtk.ListStore.new([str, Gio.Icon, str])
        self.dir_table = Gtk.TreeView.new_with_model(self.dir_store)
        self.dir_table.set_headers_visible(False)
        self.dir_table.set_property("enable-search", False)
        self.dir_table.connect("cursor-changed", self.dir_table_cursor_changed)
        self.dir_table.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        icon_cell = Gtk.CellRendererPixbuf()

        icon_col = Gtk.TreeViewColumn("icon", icon_cell)
        icon_col.add_attribute(icon_cell, "gicon", 1)

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("name", cell)
        col.add_attribute(cell, "text", 2)
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.dir_table.append_column(icon_col)
        self.dir_table.append_column(col)
        self.dir_table.show()
        self.dirlist_parent.add(self.dir_table)
        self.read_directory_settings()

        # global keybindings list
        self.keybind_table, self.keybind_store = _create_conf_keys_list()
        self.keybindings_list_parent.add(self.keybind_table)
        self.keybind_table.connect("row-activated", self.on_keybindings_row_activate)
        button_reset_keys.set_sensitive(keybindings.is_available())
        self.keybind_table.set_sensitive(keybindings.is_available())


        # kupfer interface (accelerators) keybindings list 
        self.gkeybind_table, self.gkeybind_store = _create_conf_keys_list()
        self.gkeybindings_list_parent.add(self.gkeybind_table)
        self.gkeybind_table.connect("row-activated",
                self.on_gkeybindings_row_activate)

        # Requires GTK 3.22
        try:
            self.gkeybindings_list_parent.set_propagate_natural_height(True)
        except AttributeError:
            pass

        self._show_keybindings(setctl)
        self._show_gkeybindings(setctl)

        # Connect to signals at the last point
        builder.connect_signals(self)

    def _show_keybindings(self, setctl):
        names = self.KEYBINDING_NAMES
        self.keybind_store.clear()
        for binding in sorted(names, key=lambda k: names[k]):
            accel = setctl.get_global_keybinding(binding) or ""
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(accel))
            self.keybind_store.append((names[binding], label, binding))

    def _show_gkeybindings(self, setctl):
        names = accelerators.ACCELERATOR_NAMES
        self.gkeybind_store.clear()
        for binding in sorted(names, key=lambda k: names[k]):
            accel = setctl.get_accelerator(binding) or ""
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(accel))
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
        self.dir_store.remove(rowiter)
        if store:
            have = list(os.path.normpath(row[0]) for row in self.dir_store)
            setctl = settings.GetSettingsController()
            setctl.set_directories(have)

    def on_preferenceswindow_key_press_event(self, widget, event):
        if event.keyval == Gdk.keyval_from_name("Escape"):
            self.hide()
            return True

    def on_checkstatusicon_gtk_toggled(self, widget):
        setctl = settings.GetSettingsController()
        setctl.set_show_status_icon(widget.get_active())

    def on_checkstatusicon_ai_toggled(self, widget):
        setctl = settings.GetSettingsController()
        setctl.set_show_status_icon_ai(widget.get_active())

    def _get_should_autostart(self):
        KUPFER_DESKTOP = "kupfer.desktop"
        AUTOSTART_KEY = "X-GNOME-Autostart-enabled"
        HIDDEN_KEY = "Hidden"
        autostart_dir = base.save_config_path("autostart")
        autostart_file = os.path.join(autostart_dir, KUPFER_DESKTOP)
        if not os.path.exists(autostart_file):
            return False
        try:
            dfile = desktop.DesktopEntry(autostart_file)
        except xdg_e.ParsingError as exception:
            pretty.print_error(__name__, exception)
            return False
        return ((dfile.hasKey(AUTOSTART_KEY) and
                 dfile.get(AUTOSTART_KEY, type="boolean"))
                and (not dfile.hasKey(HIDDEN_KEY) or
                     not dfile.get(HIDDEN_KEY, type="boolean")))

    def on_checkautostart_toggled(self, widget):
        KUPFER_DESKTOP = "kupfer.desktop"
        AUTOSTART_KEY = "X-GNOME-Autostart-enabled"
        HIDDEN_KEY = "Hidden"
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
            try:
                dfile = desktop.DesktopEntry(desktop_file_path)
            except xdg_e.ParsingError as exception:
                pretty.print_error(__name__, exception)
                return
            executable = dfile.getExec()
            ## append no-splash
            if "--no-splash" not in executable:
                executable += " --no-splash"
            dfile.set("Exec", executable)
        else:
            try:
                dfile = desktop.DesktopEntry(autostart_file)
            except xdg_e.ParsingError as exception:
                pretty.print_error(__name__, exception)
                return
        activestr = str(bool(widget.get_active())).lower()
        not_activestr = str(not bool(widget.get_active())).lower()
        self.output_debug("Setting autostart to", activestr)
        dfile.set(AUTOSTART_KEY, activestr)
        dfile.set(HIDDEN_KEY, not_activestr)
        ## remove the format specifiers
        executable = dfile.getExec().replace("%F", "")
        dfile.set("Exec", executable)
        dfile.write(filename=autostart_file)

    def on_entrykeybinding_changed(self, widget):
        pass

    def on_buttonkeybinding_clicked(self, widget):
        keystr = getkey_dialog.ask_for_key(keybindings.bind_key,
                    screen=widget.get_screen(),
                    parent=widget.get_toplevel())
        if keystr:
            self.entrykeybinding.set_text(keystr)
            self.output_debug("Try set keybinding with", keystr)
            keybindings.bind_key(keystr)
            setctl = settings.GetSettingsController()
            setctl.set_keybinding(keystr)

    def on_helpbutton_clicked(self, widget):
        kupferui.show_help()

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
            text = "%s" % name

            if us_filter:
                name_score = relevance.score(name, us_filter)
                fold_name_score = relevance.score(folded_name, us_filter)
                desc_score = relevance.score(desc, us_filter)
                if not name_score and not fold_name_score and desc_score < 0.9:
                    continue

            self.store.append((plugin_id, enabled, "kupfer-object", text))

    def _show_focus_topmost_plugin(self):
        try:
            first_row = next(iter(self.store))
        except StopIteration:
            return
        plugin_id = first_row[0]
        self.show_focus_plugin(plugin_id, 0)

    def on_checkplugin_toggled(self, cell, path):
        checkcol = self.columns.index("enabled")
        plugin_id = self._id_for_table_path(path)
        it = self.store.get_iter(path)
        plugin_is_enabled = not self.store.get_value(it, checkcol)
        self.store.set_value(it, checkcol, plugin_is_enabled)
        setctl = settings.GetSettingsController()
        setctl.set_plugin_enabled(plugin_id, plugin_is_enabled)
        self.plugin_sidebar_update(plugin_id)

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
        about = Gtk.VBox()
        about.set_property("spacing", 15)
        about.set_property("border-width", 5)
        info = self._plugin_info_for_id(plugin_id)
        title_label = Gtk.Label()
        m_localized_name = GLib.markup_escape_text(info["localized_name"])
        title_label.set_markup("<b><big>%s</big></b>" % m_localized_name)
        version, description, author = plugins.get_plugin_attributes(plugin_id,
                ( "__version__", "__description__", "__author__", ))
        about.pack_start(title_label, False, True, 0)
        infobox = Gtk.VBox()
        infobox.set_property("spacing", 3)
        # TRANS: Plugin info fields
        for field, val in zip((_("Description"), _("Author")),
                (description, author)):
            if not val:
                continue
            label = Gtk.Label()
            label.set_alignment(0, 0)
            label.set_markup("<b>%s</b>" % field)
            infobox.pack_start(label, False, True, 0)
            label = wrapped_label()
            label.set_alignment(0, 0)
            label.set_markup("%s" % GLib.markup_escape_text(val))
            label.set_selectable(True)
            infobox.pack_start(label, False, True, 0)
        if version:
            label = wrapped_label()
            label.set_alignment(0, 0)
            m_version = GLib.markup_escape_text(version)
            label.set_markup("<b>%s:</b> %s" % (_("Version"), m_version))
            label.set_selectable(True)
            infobox.pack_start(label, False, True, 0)
        about.pack_start(infobox, False, True, 0)

        # Check for plugin load exception
        exc_info = plugins.get_plugin_error(plugin_id)
        if exc_info is not None:
            etype, error, tb = exc_info
            # TRANS: Error message when Plugin needs a Python module to load
            import_error_localized = _("Python module '%s' is needed") % "\\1"
            import_error_pat = "No module named ([^\s]+)"
            errmsg = str(error)
            if re.match(import_error_pat, errmsg):
                errstr = re.sub(import_error_pat,
                        import_error_localized,
                        errmsg, count=1)
            elif issubclass(etype, ImportError):
                errstr = errmsg
            else:
                import traceback
                errstr = "".join(traceback.format_exception(*exc_info))

            label = wrapped_label()
            label.set_alignment(0, 0)
            label.set_markup("<b>%s</b>\n\n%s" % (
                _("Plugin could not be read due to an error:"),
                GLib.markup_escape_text(errstr),
                ))
            label.set_selectable(True)
            about.pack_start(label, False, True, 0)
        elif not plugins.is_plugin_loaded(plugin_id):
            label = Gtk.Label()
            label.set_alignment(0, 0)
            label.set_text("(%s)" % _("disabled"))
            about.pack_start(label, False, True, 0)

        wid = self._make_plugin_info_widget(plugin_id)
        about.pack_start(wid, False, True, 0)
        psettings_wid = self._make_plugin_settings_widget(plugin_id)
        if psettings_wid:
            about.pack_start(psettings_wid, False, True, 0)

        oldch = self.plugin_about_parent.get_child()
        if oldch:
            self.plugin_about_parent.remove(oldch)
        vp = Gtk.Viewport()
        vp.set_shadow_type(Gtk.ShadowType.NONE)
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
        vbox = Gtk.VBox()
        vbox.set_property("spacing", 5)
        setctl = settings.GetSettingsController()
        small_icon_size = setctl.get_config_int("Appearance", "icon_small_size")

        def make_objects_frame(objs, title):
            frame_label = Gtk.Label()
            frame_label.set_markup("<b>%s</b>" %
                                   GLib.markup_escape_text(title))
            frame_label.set_alignment(0, 0)
            objvbox = Gtk.VBox()
            objvbox.pack_start(frame_label, False, True, 0)
            objvbox.set_property("spacing", 3)
            for item in objs:
                plugin_type = plugins.get_plugin_attribute(plugin_id, item)
                if not plugin_type:
                    continue
                hbox = Gtk.HBox()
                hbox.set_property("spacing", 3)
                obj = plugin_type()
                name = str(obj)
                desc = obj.get_description() or ""
                gicon = obj.get_icon()
                im = Gtk.Image()
                im.set_property("gicon", gicon)
                im.set_property("pixel-size", small_icon_size)
                hbox.pack_start(im, False, True, 0)
                m_name = GLib.markup_escape_text(name)
                m_desc = GLib.markup_escape_text(desc)
                name_label = \
                    "%s\n<small>%s</small>" % (m_name, m_desc) if m_desc else \
                    "%s" % (m_name, )
                label = wrapped_label()
                label.set_markup(name_label)
                label.set_xalign(0.)
                hbox.pack_start(label, False, True, 0)
                objvbox.pack_start(hbox, True, True, 0)
                # Display information for application content-sources.
                if not kobject_should_show(obj):
                    continue
                try:
                    leaf_repr = obj.get_leaf_repr()
                except AttributeError:
                    continue
                if leaf_repr is None:
                    continue
                hbox = Gtk.HBox()
                hbox.set_property("spacing", 3)
                gicon = leaf_repr.get_icon()
                im = Gtk.Image()
                im.set_property("gicon", gicon)
                im.set_property("pixel-size", small_icon_size // 2)
                hbox.pack_start(Gtk.Label.new(_("Content of")), False, True, 0)
                hbox.pack_start(im, False, True, 0)
                hbox.pack_start(Gtk.Label.new(str(leaf_repr)), False, True, 0)
                objvbox.pack_start(hbox, True, True, 0)
            return objvbox

        sources = list(sources or ()) + list(text_sources or ())
        if sources:
            # TRANS: Plugin contents header
            swid = make_objects_frame(sources, _("Sources"))
            vbox.pack_start(swid, True, True, 0)
        if actions:
            # TRANS: Plugin contents header
            awid = make_objects_frame(actions, _("Actions"))
            vbox.pack_start(awid, True, True, 0)

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
            val_type = plugin_support.UserNamePassword
            backend_name = plugin_support.UserNamePassword.get_backend_name()
            if plugin_support.UserNamePassword.is_backend_encrypted():
                information = _("Using encrypted password storage: %s") % backend_name
            else:
                information = _("Using password storage: %s") % backend_name
            upass = setctl.get_plugin_config(plugin_id, key, val_type) \
                    or plugin_support.UserNamePassword()
            user_password = ask_user_credentials(upass.username, upass.password, information)
            if user_password:
                upass.username, upass.password = user_password
                setctl.set_plugin_config(plugin_id, key, upass, val_type)
        return callback

    def _make_plugin_settings_widget(self, plugin_id):
        plugin_settings = plugins.get_plugin_attribute(plugin_id,
                plugins.settings_attribute)
        if not plugin_settings:
            return None

        title_label = Gtk.Label()
        # TRANS: Plugin-specific configuration (header)
        title_label.set_markup("<b>%s</b>" % _("Configuration"))
        title_label.set_alignment(0, 0)

        vbox = Gtk.VBox()
        vbox.pack_start(title_label, False, True, 0)
        #vbox.set_property("spacing", 5)

        plugin_settings_keys = iter(plugin_settings) if plugin_settings else ()
        for setting in plugin_settings_keys:
            typ = plugin_settings.get_value_type(setting)
            alternatives = plugin_settings.get_alternatives(setting)
            tooltip = plugin_settings.get_tooltip(setting)
            wid = None
            hbox = Gtk.HBox()
            hbox.set_property("spacing", 10)
            if tooltip:
                hbox.set_tooltip_text(tooltip)
            label = plugin_settings.get_label(setting)

            if issubclass(typ, plugin_support.UserNamePassword):
                wid = Gtk.Button(label or _("Set username and password"))
                wid.connect("clicked", self._get_plugin_credentials_callback(
                        plugin_id, setting))
                hbox.pack_start(wid, False, True, 0)
                vbox.pack_start(hbox, False, True, 0)
                continue

            label_wid = wrapped_label(label, maxwid=200)
            label_wid.set_xalign(0.)
            if issubclass(typ, str):
                if alternatives:
                    wid = Gtk.ComboBoxText.new()
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
                    wid = Gtk.Entry()
                    wid.set_text(plugin_settings[setting])
                    wid.connect("changed", self._get_plugin_change_callback(
                        plugin_id, setting, typ, "get_text",
                        no_false_values=True))
                hbox.pack_start(label_wid, False, True, 0)
                hbox.pack_start(wid, True, True, 0)

            elif issubclass(typ, bool):
                wid = Gtk.CheckButton.new_with_label(label)
                wid.set_active(plugin_settings[setting])
                hbox.pack_start(wid, False, True, 0)
                wid.connect("toggled", self._get_plugin_change_callback(
                    plugin_id, setting, typ, "get_active"))
            elif issubclass(typ, int):
                wid = Gtk.SpinButton()
                wid.set_increments(1, 1)
                wid.set_range(0, 1000)
                wid.set_value(plugin_settings[setting])
                hbox.pack_start(label_wid, False, True, 0)
                hbox.pack_start(wid, False, True, 0)
                wid.connect("changed", self._get_plugin_change_callback(
                    plugin_id, setting, typ, "get_text", no_false_values=True))
            vbox.pack_start(hbox, False, True, 0)

        vbox.show_all()
        return vbox

    def on_buttonadddirectory_clicked(self, widget):
        # TRANS: File Chooser Title
        chooser_dialog = Gtk.FileChooserDialog(title=_("Choose a Directory"),
                action=Gtk.FileChooserAction.SELECT_FOLDER,
                buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                    Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        chooser_dialog.set_select_multiple(True)
        if chooser_dialog.run() == Gtk.ResponseType.ACCEPT:
            for selected_dir in chooser_dialog.get_filenames():
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
        keystr = getkey_dialog.ask_for_key(bind_func, curr_key,
                                screen=treeview.get_screen(),
                                parent=treeview.get_toplevel())
        if keystr == '':
            keybindings.bind_key(None, self.KEYBINDING_TARGETS[keybind_id])
            setctl.set_global_keybinding(keybind_id, keystr)
            self.keybind_store.set_value(it, 1, '')
        elif keystr is not None:
            setctl.set_global_keybinding(keybind_id, keystr)
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
            self.keybind_store.set_value(it, 1, label)

    def _is_good_keystr(self, keystr):
        # Reject single letters so you can't bind 'A' etc
        if keystr is None:
            return
        label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
        ulabel = kupferstring.tounicode(label)
        return not (len(ulabel) == 1 and ulabel.isalnum())

    def on_gkeybindings_row_activate(self, treeview, path, view_column):
        it = self.gkeybind_store.get_iter(path)
        keybind_id = self.gkeybind_store.get_value(it, 2)
        setctl = settings.GetSettingsController()
        curr_key = setctl.get_accelerator(keybind_id)
        keystr = getkey_dialog.ask_for_key(self._is_good_keystr,
                previous_key=curr_key, screen=treeview.get_screen(),
                parent=treeview.get_toplevel())
        if keystr is not None:
            setctl.set_accelerator(keybind_id, keystr)
            label = Gtk.accelerator_get_label(*Gtk.accelerator_parse(keystr))
            self.gkeybind_store.set_value(it, 1, label)

    def on_button_reset_keys_clicked(self, button):
        if self.ask_user_for_reset_keybinding():
            setctl = settings.GetSettingsController()
            setctl.reset_keybindings()
            self._show_keybindings(setctl)
            # Unbind all before re-binding
            for keybind_id, target in self.KEYBINDING_TARGETS.items():
                keybindings.bind_key(None, target)
            for keybind_id, target in self.KEYBINDING_TARGETS.items():
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

    def on_radio_action_accel_alt(self, widget):
        if widget.get_active():
            setctl = settings.GetSettingsController()
            setctl.set_action_accelerator_modifier('alt')

    def on_radio_action_accel_ctrl(self, widget):
        if widget.get_active():
            setctl = settings.GetSettingsController()
            setctl.set_action_accelerator_modifier('ctrl')

    def dir_table_cursor_changed(self, table):
        curpath, curcol = table.get_cursor()
        if not curpath or not self.dir_store:
            self.buttonremovedirectory.set_sensitive(False)
            return
        self.buttonremovedirectory.set_sensitive(True)

    def on_terminal_combobox_changed(self, widget):
        setctl = settings.GetSettingsController()
        itr = widget.get_active_iter()
        if itr:
            term_id = widget.get_model().get_value(itr, 1)
            setctl.set_preferred_tool('terminal', term_id)

    def on_icons_combobox_changed(self, widget):
        setctl = settings.GetSettingsController()
        itr = widget.get_active_iter()
        if itr:
            term_id = widget.get_model().get_value(itr, 1)
            setctl.set_preferred_tool('icon_renderer', term_id)

    def on_icons_large_size_changed(self, widget):
        setctl = settings.GetSettingsController()
        itr = widget.get_active_iter()
        if itr:
            val = widget.get_active_text()
            setctl.set_large_icon_size(val)

    def on_icons_small_size_changed(self, widget):
        setctl = settings.GetSettingsController()
        itr = widget.get_active_iter()
        if itr:
            val = widget.get_active_text()
            setctl.set_small_icon_size(val)

    def _update_alternative_combobox(self, category_key, combobox):
        """
        Alternatives changed
        """
        combobox_store = combobox.get_model()
        combobox_store.clear()
        setctl = settings.GetSettingsController()
        term_id = setctl.get_preferred_tool(category_key)
        # fill in the available alternatives
        alternatives = utils.locale_sort(
                setctl.get_valid_alternative_ids(category_key), key=lambda t:t[1])
        term_iter = None
        for (id_, name) in alternatives:
            _it = combobox_store.append((name, id_))
            if id_ == term_id:
                term_iter = _it
        # Update selection
        term_iter = term_iter or combobox_store.get_iter_first()
        combobox.set_sensitive(len(combobox_store) > 1)
        if term_iter:
            combobox.set_active_iter(term_iter)


    def _on_alternatives_changed(self, setctl, category_key):
        if category_key == 'terminal':
            self._update_alternative_combobox(category_key,
                    self.terminal_combobox)
        elif category_key == 'icon_renderer':
            self._update_alternative_combobox(category_key,
                    self.icons_combobox)

    def on_preferences_notebook_switch_page(self, notebook, page, page_num):
        ## focus the search box on the plugin tab
        if page_num == PLUGIN_LIST_PAGE:
            GLib.idle_add(self.entry_plugins_filter.grab_focus)

    def show(self, timestamp):
        self.window.present_with_time(timestamp)

    def show_on_screen(self, timestamp, screen):
        self.window.set_screen(screen)
        self.show(timestamp)
        ## focus the search box on the plugin tab
        if self.preferences_notebook.get_current_page() == PLUGIN_LIST_PAGE:
            self.entry_plugins_filter.grab_focus()

    def show_focus_plugin(self, plugin_id, timestamp):
        """
        Open and show information about plugin @plugin_id
        """
        try:
            table_path = self._table_path_for_id(plugin_id)
        except ValueError:
            self.entry_plugins_filter.set_text("")
            self._refresh_plugin_list()
            table_path = self._table_path_for_id(plugin_id)
        self.table.set_cursor(table_path)
        self.table.scroll_to_cell(table_path)
        self.preferences_notebook.set_current_page(PLUGIN_LIST_PAGE)
        self.window.present_with_time(timestamp)

    def hide(self):
        self.window.hide()
    def _close_window(self, *ignored):
        self.hide()
        return True

    def ask_user_for_reset_keybinding(self):
        dlg = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION)
        dlg.set_markup(_("Reset all shortcuts to default values?"))
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE,
                _('Reset'), Gtk.ResponseType.ACCEPT)
        result = dlg.run() == Gtk.ResponseType.ACCEPT
        dlg.destroy()
        return result


_conf_keys_list_columns = [{"key": "name", "type":str, 'header': _('Command')},
        {"key": "key", "type": str, 'header': _('Shortcut') },
        {"key": "keybinding_id", "type": str, 'header':  None}]
_conf_keys_list_column_types = [c["type"] for c in _conf_keys_list_columns]

def _create_conf_keys_list():
    keybind_store = Gtk.ListStore.new(_conf_keys_list_column_types)
    keybind_table = Gtk.TreeView.new_with_model(keybind_store)
    for idx, col in enumerate(_conf_keys_list_columns):
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(col['header'], renderer, text=idx)
        column.set_visible(col['header'] is not None)
        keybind_table.append_column(column)
    keybind_table.set_property("enable-search", False)
    keybind_table.set_headers_visible(True)
    keybind_table.show()
    return keybind_table, keybind_store


_preferences_window = None

def GetPreferencesWindowController():
    global _preferences_window
    if _preferences_window is None:
        _preferences_window = PreferencesWindowController()
    return _preferences_window

class SourceListController (object):
    def __init__(self, parent_widget):
        columns = [
            {"key": "source", "type": GObject.TYPE_PYOBJECT },
            {"key": "plugin_id", "type": str },
            {"key": "toplevel", "type": bool },
            {"key": "icon", "type": Gio.Icon },
            {"key": "text", "type": str },
        ]
        # setup plugin list table
        column_types = [c["type"] for c in columns]
        self.columns = [c["key"] for c in columns]
        self.store = Gtk.ListStore(*column_types)
        self.table = Gtk.TreeView.new_with_model(self.store)
        self.table.set_headers_visible(False)
        self.table.set_property("enable-search", False)
        #self.table.connect("cursor-changed", self.plugin_table_cursor_changed)
        self.table.get_selection().set_mode(Gtk.SelectionMode.NONE)

        checkcell = Gtk.CellRendererToggle()
        checkcol = Gtk.TreeViewColumn("item", checkcell)
        checkcol.add_attribute(checkcell, "active",
                self.columns.index("toplevel"))
        checkcell.connect("toggled", self.on_checktoplevel_enabled)

        icon_cell = Gtk.CellRendererPixbuf()
        icon_cell.set_property("height", LIST_ICON_SIZE)
        icon_cell.set_property("width", LIST_ICON_SIZE)

        icon_col = Gtk.TreeViewColumn("icon", icon_cell)
        icon_col.add_attribute(icon_cell, "gicon",
                self.columns.index("icon"))

        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("item", cell)
        col.add_attribute(cell, "text", self.columns.index("text"))

        self.table.append_column(checkcol)
        self.table.append_column(icon_col)
        self.table.append_column(col)

        self._refresh()
        self.table.show()
        parent_widget.add(self.table)

        setctl = settings.GetSettingsController()
        setctl.connect("plugin-enabled-changed", self._refresh)

    def _refresh(self, *ignored):
        self.store.clear()
        setctl = settings.GetSettingsController()
        sc = sources.GetSourceController()
        srcs = sorted(sc.get_sources(), key=str)

        for src in srcs:
            name = str(src)
            plugin_id = sc.get_plugin_id_for_object(src)
            if not plugin_id or setctl.get_plugin_is_hidden(plugin_id):
                continue
            if not kobject_should_show(src):
                continue
            gicon = src.get_icon()
            toplevel = setctl.get_source_is_toplevel(plugin_id, src)

            self.store.append((src, plugin_id, toplevel, gicon, name))

    def on_checktoplevel_enabled(self, cell, path):
        it = self.store.get_iter(path)
        checkcol = self.columns.index("toplevel")
        idcol = self.columns.index("plugin_id")
        srccol = self.columns.index("source")
        is_toplevel = not self.store.get_value(it, checkcol)
        plugin_id = self.store.get_value(it, idcol)
        src = self.store.get_value(it, srccol)

        sc = sources.GetSourceController()
        sc.set_toplevel(src, is_toplevel)

        setctl = settings.GetSettingsController()
        setctl.set_source_is_toplevel(plugin_id, src, is_toplevel)
        self.store.set_value(it, checkcol, is_toplevel)


def supports_app_indicator():
    try:
        gi.require_version("AppIndicator3", "0.1")
    except ValueError:
        return False
    else:
        return True

