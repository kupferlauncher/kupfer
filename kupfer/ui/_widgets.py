# Distributed under terms of the GPLv3 license.

"""
Custom widgets used mostly in Preferences Dialog
"""
from __future__ import annotations

import os
import typing as ty

from gi.repository import Gtk, Gio, Pango

from kupfer import icons, launch, plugin_support
from kupfer.core import settings

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class DirsSelectWidget(Gtk.Bin):  # type: ignore
    """Widgets with list of folders and buttons to add/remove folder into."""

    def __init__(
        self,
        plugin_id: str,
        setting: str,
        plugin_settings: plugin_support.PluginSettings,
    ):
        """Create widgets.
        Args:
            `plugin_id`: plugin id
            `setting`: name of parameter
            `plugin_support`: object PluginSettings for given plugin
        """
        super().__init__()

        self.plugin_id = plugin_id
        self.setting = setting
        self.plugin_settings = plugin_settings

        self.model = Gtk.ListStore.new([str, Gio.Icon, str])
        self.view = Gtk.TreeView.new_with_model(self.model)

        # pylint: disable=no-member
        self.btn_add = Gtk.Button.new_from_stock(Gtk.STOCK_ADD)
        # pylint: disable=no-member
        self.btn_del = Gtk.Button.new_from_stock(Gtk.STOCK_REMOVE)

        self._configure_model()
        self._create_layout()

        if dirs := plugin_settings[setting]:
            self._add_dirs(dirs)

        self.view.connect("cursor-changed", self._on_cursor_changed)
        self.btn_del.connect("clicked", self._on_del_clicked)
        self.btn_add.connect("clicked", self._on_add_clicked)

    def _configure_model(self):
        view = self.view

        view.set_headers_visible(False)
        view.set_property("enable-search", False)
        view.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        icon_cell = Gtk.CellRendererPixbuf()
        icon_col = Gtk.TreeViewColumn("icon", icon_cell)
        icon_col.add_attribute(icon_cell, "gicon", 1)

        cell = Gtk.CellRendererText()
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)

        col = Gtk.TreeViewColumn("name", cell)
        col.add_attribute(cell, "text", 2)

        view.append_column(icon_col)
        view.append_column(col)
        view.show()

    def _create_layout(self):
        box = Gtk.VBox()
        box.set_spacing(3)

        scrollwin = Gtk.ScrolledWindow()
        # pylint: disable=no-member
        scrollwin.set_shadow_type(type=Gtk.ShadowType.IN)
        scrollwin.set_hexpand(True)
        scrollwin.set_size_request(50, 100)
        # pylint: disable=no-member
        scrollwin.add(self.view)

        box.pack_start(scrollwin, True, True, 0)

        # buttons
        bbox = Gtk.HButtonBox()
        bbox.set_property("layout-style", Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.btn_del, False, False, 0)
        bbox.pack_start(self.btn_add, False, False, 0)
        box.pack_end(bbox, True, True, 0)

        box.set_hexpand(True)
        self.add(box)

    def _add_dirs(self, dirs: list[str]) -> None:
        for directory in dirs:
            directory = os.path.expanduser(directory)
            dispname = launch.get_display_path_for_bytestring(directory)
            gicon = icons.get_gicon_for_file(directory)
            self.model.append((directory, gicon, dispname))

    def _on_cursor_changed(self, table: Gtk.TreeView) -> None:
        curpath, _curcol = table.get_cursor()
        self.btn_del.set_sensitive(bool(curpath))

    def _on_del_clicked(self, widget: Gtk.Widget) -> None:
        curpath, _curcol = self.view.get_cursor()
        if curpath:
            rowiter = self.model.get_iter(curpath)
            self.model.remove(rowiter)
            self._save()

    def _on_add_clicked(self, widget: Gtk.Widget) -> None:
        # TRANS: File Chooser Title
        chooser_dialog = Gtk.FileChooserDialog(
            title=_("Choose a Directory"),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.REJECT,
                Gtk.STOCK_OK,
                Gtk.ResponseType.ACCEPT,
            ),
        )
        chooser_dialog.set_select_multiple(True)

        # pylint: disable=no-member
        if chooser_dialog.run() == Gtk.ResponseType.ACCEPT:
            # pylint: disable=no-member
            have = self.current_dirs()
            new_dirs = [
                directory
                for directory in chooser_dialog.get_filenames()
                if directory not in have
            ]
            self._add_dirs(new_dirs)
            self._save()

        chooser_dialog.hide()

    def current_dirs(self) -> list[str]:
        return [os.path.normpath(row[0]) for row in self.model]

    def _save(self) -> None:
        setctl = settings.get_settings_controller()
        setctl.set_plugin_config(
            self.plugin_id, self.setting, self.current_dirs(), list
        )


class FileDirSelectWidget(Gtk.Bin):  # type: ignore
    """Widgets with entry and buttons that allow to select file or directory."""

    def __init__(
        self,
        plugin_id: str,
        setting: str,
        plugin_settings: plugin_support.PluginSettings,
        kind: str,
    ):
        """Create widgets.
        Args:
            `plugin_id`: plugin id
            `setting`: name of parameter
            `plugin_support`: object PluginSettings for given plugin
            `kind`: what user can select via dialog: 'choose_file' or
                'choose_directory'
        """
        assert kind in ("choose_directory", "choose_file")

        super().__init__()
        self.plugin_id = plugin_id
        self.setting = setting
        self.plugin_settings = plugin_settings
        self.kind = kind

        self.entry = Gtk.Entry()

        # pylint: disable=no-member
        self.btn_add = Gtk.Button.new_from_stock(Gtk.STOCK_FIND)
        # pylint: disable=no-member
        self.btn_del = Gtk.Button.new_from_stock(Gtk.STOCK_CLEAR)

        self._create_layout()

        self.entry.set_text(plugin_settings[setting])

        self.btn_del.connect("clicked", self._on_del_clicked)
        self.btn_add.connect("clicked", self._on_add_clicked)
        self.entry.connect("changed", self._on_change)

    def _create_layout(self):
        box = Gtk.VBox()
        box.set_spacing(3)

        box.pack_start(self.entry, True, True, 0)

        # buttons
        bbox = Gtk.HButtonBox()
        bbox.set_property("layout-style", Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.btn_del, False, False, 0)
        bbox.pack_start(self.btn_add, False, False, 0)
        box.pack_end(bbox, True, True, 0)

        box.set_hexpand(True)
        self.add(box)

    def _on_change(self, widget: Gtk.Widget) -> None:
        setctl = settings.get_settings_controller()
        setctl.set_plugin_config(
            self.plugin_id, self.setting, widget.get_text(), str
        )

    def _on_del_clicked(self, widget: Gtk.Widget) -> None:
        self.entry.set_text("")

    def _on_add_clicked(self, widget: Gtk.Widget) -> None:
        # TRANS: File Chooser Title
        if self.kind == "choose_directory":
            title = _("Choose a Directory")
            action = Gtk.FileChooserAction.SELECT_FOLDER
        else:
            title = _("Choose a File")
            action = Gtk.FileChooserAction.OPEN

        chooser_dialog = Gtk.FileChooserDialog(
            title=title,
            action=action,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.REJECT,
                Gtk.STOCK_OK,
                Gtk.ResponseType.ACCEPT,
            ),
        )
        chooser_dialog.set_select_multiple(False)
        if fname := self.entry.get_text():
            fname = os.path.expanduser(fname)
            chooser_dialog.set_filename(fname)

        # pylint: disable=no-member
        if chooser_dialog.run() == Gtk.ResponseType.ACCEPT:
            # pylint: disable=no-member
            fname = chooser_dialog.get_filename()
            fname = os.path.normpath(fname)
            self.entry.set_text(fname)

        chooser_dialog.hide()
