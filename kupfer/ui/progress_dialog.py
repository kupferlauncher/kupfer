# note: not used

from __future__ import annotations

import functools
import typing as ty

# NOTE: was glib; changed to gio.repo.GLib
from gi.repository import GLib, Gtk

from kupfer import config, version

T = ty.TypeVar("T")


def idle_call(func: ty.Callable[..., T]) -> ty.Callable[..., T]:
    @functools.wraps(func)
    def idle_wrapper(*args):
        GLib.idle_add(func, *args)  # pylint: disable=no-member

    return idle_wrapper


_HEADER_MARKUP = '<span weight="bold" size="larger">%s</span>'


class ProgressDialogController:
    def __init__(
        self, title: str, header: str | None = None, max_value: int = 100
    ):
        """Create a new progress dialog

        @header: first line of dialog

        The methods show, hide and update are all wrapped to be
        safe to call from any thread.
        """
        self.aborted = False
        self._max_value = float(max_value)
        ui_file = config.get_data_file("progress_dialog.ui")
        self._construct_dialog(ui_file, title, header)

    @idle_call
    def _construct_dialog(self, ui_file: str, title: str, header: str) -> None:
        builder = Gtk.Builder()
        builder.set_translation_domain(version.PACKAGE_NAME)

        builder.add_from_file(ui_file)
        builder.connect_signals(self)  # pylint: disable=no-member
        self._window = builder.get_object("window_progress")
        self._button_abort = builder.get_object("button_abort")
        self._progressbar = builder.get_object("progressbar")
        self._label_info = builder.get_object("label_info")

        label_header = builder.get_object("label_header")
        if header:
            label_header.set_markup(
                _HEADER_MARKUP % GLib.markup_escape_text(header)
            )
        else:
            label_header.hide()

        self._window.set_title(title)
        self.update(0, "", "")

    def on_button_abort_clicked(self, widget: Gtk.Button) -> None:
        self.aborted = True
        self._button_abort.set_sensitive(False)

    @idle_call
    def show(self) -> None:
        self._window.present()

    @idle_call
    def hide(self) -> None:
        self._window.hide()

    @idle_call
    def update(self, value: int | float, label: str, text: str) -> bool:
        """Update dialog information.

        @value: value to set for progress bar
        @label: current action (displayed in emphasized style)
        @text: current information (normal style)

        @return true when abort button was pressed
        """
        self._progressbar.set_fraction(min(value / self._max_value, 1.0))
        self._label_info.set_markup(
            "<b>"
            + GLib.markup_escape_text(label)
            + "</b>"
            + GLib.markup_escape_text(text)
        )
        return self.aborted
