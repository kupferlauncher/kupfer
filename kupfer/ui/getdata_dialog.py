from __future__ import annotations

from gi.repository import Gdk, Gtk

from kupfer import config, version

__all__ = ["GetDataDialog", "ask_for_text"]


class GetDataDialog:
    def __init__(
        self,
        title: str,
        message: str = "",
        screen: Gdk.Screen | None = None,
        parent: Gtk.Window | None = None,
    ):
        """
        screen: Screen to use
        parent: Parent toplevel window
        """
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)

        builder.add_from_file(config.get_data_file("getdata_dialog.ui"))
        builder.connect_signals(self)  # pylint: disable=no-member
        self.window = builder.get_object("dialoggetdata")
        self._box_fields = builder.get_object("box_fields")
        builder.get_object("label_title").set_text(title)
        if message:
            builder.get_object("label_message").set_text(message)
        else:
            builder.get_object("label_message").hide()

        if screen:
            self.window.set_screen(screen)

        if parent:
            self.window.set_transient_for(parent)

        self._text = None
        self._fields: dict[str, Gtk.Widget] = {}
        self._result: dict[str, str] | None = None

    def add_field(self, name: str, label: str, value: str) -> None:
        """Add text entry to dialog with `label` and `value`. `name` is internal
        name of value returned by dialog."""
        row = len(self._fields)

        wlabel = Gtk.Label()
        wlabel.set_alignment(0, 0.5)  # pylint: disable=no-member
        wlabel.set_markup(label)
        wlabel.set_selectable(False)
        self._box_fields.attach(wlabel, 0, row, 1, 1)

        widget = Gtk.Entry()
        widget.set_text(value)
        widget.set_hexpand(True)
        widget.set_activates_default(True)
        self._box_fields.attach(widget, 1, row, 1, 1)

        self._fields[name] = widget

    def run(self) -> dict[str, str] | None:
        """Run dialog, return key codes or None when user press cancel"""
        self._box_fields.show_all()
        self.window.set_keep_above(True)
        self.window.run()
        self.window.destroy()
        return self._result

    def on_buttonok_activate(self, _widget: Gtk.Widget) -> bool:
        self._result = {n: w.get_text() for n, w in self._fields.items()}
        self.window.hide()
        return True

    def on_buttonclose_activate(self, _widget: Gtk.Widget) -> bool:
        self.window.hide()
        return True


def ask_for_text(
    title: str,
    message: str,
    label: str = "",
    value: str = "",
    screen: Gdk.Screen | None = None,
    parent: Gtk.Window | None = None,
) -> str | None:
    dlg = GetDataDialog(
        title,
        message,
        screen=screen,
        parent=parent,
    )
    dlg.add_field("text", label, value)
    res = dlg.run()
    return res["text"] if res else None
