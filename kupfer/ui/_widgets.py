# Distributed under terms of the GPLv3 license.

"""
Custom widgets used mostly in Preferences Dialog
"""

from __future__ import annotations

import os
import re
import traceback
import typing as ty

from gi.repository import Gio, GLib, Gtk

from kupfer import icons, launch, plugin_support
from kupfer.core import plugins, settings
from kupfer.obj import KupferObject, Source

if ty.TYPE_CHECKING:
    from gettext import gettext as _

    from kupfer.support import types as kty


# pylint: disable=too-few-public-methods
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
        self.btn_add = Gtk.Button.new_from_icon_name("add", Gtk.IconSize.BUTTON)
        self.btn_add.always_show_image = True
        self.btn_add.set_label(_("Add"))
        # pylint: disable=no-member
        self.btn_del = Gtk.Button.new_from_icon_name(
            "remove", Gtk.IconSize.BUTTON
        )
        self.btn_del.always_show_image = True
        self.btn_del.set_label(_("Remove"))

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
        setctl = settings.get_settings_controller()
        cell.set_property("ellipsize", setctl.get_ellipsize_mode())

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
        for directory in map(os.path.expanduser, dirs):
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


# pylint: disable=too-few-public-methods
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

        self.btn_add = Gtk.Button.new_from_icon_name(
            "fileopen", Gtk.IconSize.BUTTON  # pylint: disable=no-member
        )
        self.btn_add.always_show_image = True
        self.btn_add.set_label(_("Select"))
        self.btn_clear = Gtk.Button.new_from_icon_name(
            "editclear", Gtk.IconSize.BUTTON  # pylint: disable=no-member
        )
        self.btn_clear.always_show_image = True
        self.btn_clear.set_label(_("Clear"))

        self._create_layout()

        self.entry.set_text(plugin_settings[setting])

        self.btn_clear.connect("clicked", self._on_del_clicked)
        self.btn_add.connect("clicked", self._on_add_clicked)
        self.entry.connect("changed", self._on_change)

    def _create_layout(self):
        box = Gtk.VBox()
        box.set_spacing(3)

        box.pack_start(self.entry, True, True, 0)

        # buttons
        bbox = Gtk.HButtonBox()
        bbox.set_property("layout-style", Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.btn_clear, False, False, 0)
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
            chooser_dialog.set_filename(fname)  # pylint: disable=no-member

        # pylint: disable=no-member
        if chooser_dialog.run() == Gtk.ResponseType.ACCEPT:
            # pylint: disable=no-member
            fname = chooser_dialog.get_filename()
            fname = os.path.normpath(fname)
            self.entry.set_text(fname)

        chooser_dialog.hide()


# pylint: disable=too-few-public-methods
class ObjectsInfoWidget(Gtk.Bin):  # type: ignore
    """Widget with list of `objs` (sources, actions): name, description."""

    def __init__(
        self,
        plugin_id: str,
        objs: ty.Iterable[str],
    ) -> None:
        super().__init__()

        setctl = settings.get_settings_controller()
        small_icon_size = setctl.get_config_int("Appearance", "icon_small_size")

        box = Gtk.Grid()
        box.set_row_spacing(6)
        box.set_column_spacing(12)

        for row, item in enumerate(objs):
            plugin_type = plugins.get_plugin_attribute(plugin_id, item)
            if not plugin_type:
                continue

            obj: KupferObject = plugin_type()

            # object icon
            image = Gtk.Image()
            image.set_property("gicon", obj.get_icon())
            image.set_property("pixel-size", small_icon_size)
            image.set_alignment(0, 0)  # pylint: disable=no-member
            box.attach(image, 0, row, 1, 1)

            ibox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 3)
            # name and description
            ibox.pack_start(self._create_label(obj), False, True, 0)
            box.attach(ibox, 1, row, 1, 1)

            # Display information for application content-sources.
            # only sources have leaf representation
            if isinstance(obj, Source):
                _valid, leaf_repr = obj.get_valid_leaf_repr()
                if leaf_repr is not None:
                    hbox = self._create_leaves_info(leaf_repr, small_icon_size)
                    ibox.pack_start(hbox, True, True, 0)

        self.add(box)

    def _create_label(self, obj: KupferObject) -> Gtk.Label:
        name_label = GLib.markup_escape_text(str(obj))  # name
        if desc := GLib.markup_escape_text(obj.get_description() or ""):
            name_label = f"{name_label}\n<small>{desc}</small>"

        label = Gtk.Label()
        label.set_alignment(0, 0)  # pylint: disable=no-member
        label.set_markup(name_label)
        label.set_line_wrap(True)  # pylint: disable=no-member
        label.set_selectable(True)
        return label

    def _create_leaves_info(
        self, leaf_repr: KupferObject, small_icon_size: int
    ) -> Gtk.Box:
        hbox = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        image = Gtk.Image()
        image.set_property("gicon", leaf_repr.get_icon())
        image.set_property("pixel-size", small_icon_size // 2)
        hbox.pack_start(Gtk.Label.new(_("Content of")), False, True, 0)
        hbox.pack_start(image, False, True, 0)
        hbox.pack_start(Gtk.Label.new(str(leaf_repr)), False, True, 0)
        return hbox


# pylint: disable=too-few-public-methods
class PluginAboutWidget(Gtk.Bin):  # type: ignore
    """Widget with basic information about plugin."""

    def __init__(self, plugin_id: str, info: dict[str, ty.Any]) -> None:
        super().__init__()

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 12)

        ver, description, author = plugins.get_plugin_attributes(
            plugin_id,
            (
                plugins.PluginAttr.VERSION,
                plugins.PluginAttr.DESCRIPTION,
                plugins.PluginAttr.AUTHOR,
            ),
        )
        infobox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 6)

        # TRANS: Plugin info fields
        for field, val in (
            (_("Description"), description),
            (_("Author"), author),
            (_("Version"), ver),
        ):
            if sbox := self._create_title_val_label_box(field, val):
                infobox.pack_start(sbox, False, True, 0)

        box.pack_start(infobox, False, True, 0)

        errormsg = None
        # Check for plugin load exception
        if (exc_info := plugins.get_plugin_error(plugin_id)) is not None:
            errstr = _format_exc_info(exc_info)
            errormsg = "".join(
                (
                    "<b>",
                    _("Plugin could not be read due to an error:"),
                    "</b>\n\n",
                    GLib.markup_escape_text(errstr),
                )
            )
        elif not plugins.is_plugin_loaded(plugin_id):
            errormsg = (
                "<i>"
                + GLib.markup_escape_text(_("Plugin is disabled"))
                + "</i>"
            )

        if errormsg:
            label = Gtk.Label()
            label.set_markup(errormsg)
            label.set_alignment(0, 0)  # pylint: disable=no-member
            label.set_line_wrap(True)  # pylint: disable=no-member
            label.set_selectable(True)
            box.pack_start(label, False, True, 0)

        self.add(box)

    def _create_title_val_label_box(
        self, title: str, value: str
    ) -> Gtk.Box | None:
        if not value:
            return None

        sbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 3)
        for label_text in (f"<b>{title}</b>", GLib.markup_escape_text(value)):
            label = Gtk.Label()
            label.set_markup(label_text)
            label.set_alignment(0, 0)  # pylint: disable=no-member
            label.set_line_wrap(True)  # pylint: disable=no-member
            label.set_selectable(True)
            sbox.pack_start(label, False, True, 0)

        return sbox


def _format_exc_info(exc_info: kty.ExecInfo) -> str:
    """Format ExecInfo to presentable form."""
    etype, error, _tb = exc_info
    import_error_pat = r"No module named ([^\s]+)"
    errmsg = str(error)

    if re.match(import_error_pat, errmsg):
        # TRANS: Error message when Plugin needs a Python module to load
        import_error_localized = _("Python module '%s' is needed") % "\\1"
        return re.sub(import_error_pat, import_error_localized, errmsg, count=1)

    if etype and issubclass(etype, ImportError):
        return errmsg

    return "".join(traceback.format_exception(*exc_info))


def new_label_header(
    parent: Gtk.Box | None, markup: str, tooltip: str | None = None
) -> Gtk.Label:
    """Return "header" label with `markup` text and optional `tooltip`.
    Add it to `parent` box if given. Return new label object."""
    markup = GLib.markup_escape_text(markup)
    return new_label(
        parent, f"<b>{markup}</b>", selectable=False, tooltip=tooltip
    )


def new_label(  # pylint: disable=keyword-arg-before-vararg
    parent: Gtk.Box | None = None,
    /,
    *markup: str,
    selectable: bool = True,
    tooltip: str | None = None,
) -> Gtk.Label:
    """Create new label with `markup` text (concatenated).
    Set optional parameters: `selectable` (default True), `tooltip`.
    If `parent` box is given, add label to box.
    Return widget object."""
    text = "".join(markup)
    label = Gtk.Label()
    label.set_alignment(0, 0.5)  # pylint: disable=no-member
    label.set_markup(text)
    label.set_line_wrap(True)  # pylint: disable=no-member
    label.set_selectable(selectable)

    if tooltip:
        label.set_tooltip_text(tooltip)

    if parent:
        parent.pack_start(label, False, True, 0)

    return label
