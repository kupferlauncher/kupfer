from __future__ import annotations

import contextlib
import os
import typing as ty
from dataclasses import dataclass

from gi.repository import Gdk, Gtk

from kupfer.support import pretty
from kupfer.ui import keybindings


def try_close_unused_displays(screen: Gdk.Screen) -> None:
    """Try to close inactive displays.

    `screen` is current GdkScreen.

    Take all GtkWindow that are hidden, and move to the
    current screen. If no windows remain then we close
    the display, but we never close the default display.
    """

    skip_displays = [
        d.get_name()
        for d in (screen.get_display(), Gdk.Display.get_default())
        if d
    ]
    if not skip_displays:
        pretty.print_error(__name__, "empty skip_displays")
        return

    dmgr = Gdk.DisplayManager.get()
    for disp in dmgr.list_displays():
        dname = disp.get_name()
        if dname in skip_displays:
            continue

        pretty.print_debug(__name__, "Trying to close", dname)
        open_windows = 0
        for window in Gtk.Window.list_toplevels():
            # find windows on @disp
            if window.get_screen().get_display().get_name() != dname:
                continue

            if not window.get_property("visible"):
                pretty.print_debug(__name__, "Moving window", window.get_name())
                pretty.print_debug(__name__, "Moving", window.get_title())
                window.set_screen(screen)
            else:
                pretty.print_debug(__name__, "Open window blocks close")
                open_windows += 1

        if not open_windows:
            pretty.print_debug(__name__, "Closing display", dname)
            disp.close()


class GUIEnvironmentContext:
    """Context object for action execution in the current GUI context"""

    def __init__(
        self, timestamp: int, screen: Gdk.Screen | None = None
    ) -> None:
        self._timestamp = timestamp
        self._screen: Gdk.Screen = screen or Gdk.Screen.get_default()

    def __repr__(self):
        return (
            f"<{type(self).__name__} "
            f"time={self._timestamp!r} screen={self._screen!r}>"
        )

    @classmethod
    def ensure_display_open(cls, display_name: str | None) -> Gdk.Display:
        """Get GdkDisplay for `display_name` or return default if `display_name`
        is None or invalid/unavailable."""
        # NOTE: display parameter was not supported; added (k)
        if disp := Gdk.Display.open(display_name):
            return disp

        return Gdk.DisplayManager.get().get_default_display()

    def get_timestamp(self) -> int:
        return self._timestamp

    def get_startup_notification_id(self) -> str:
        """Get new notification id."""
        return _make_startup_notification_id(self.get_timestamp())

    def get_display(self) -> str:
        """Return the display name to show new windows on."""
        return ty.cast(str, self._screen.make_display_name())

    def get_screen(self) -> Gdk.Screen:
        return self._screen

    def present_window(self, window: Gtk.Window) -> None:
        """Show and present `window` on the current workspace, screen & display
        as appropriate."""
        window.set_screen(self.get_screen())
        window.present_with_time(self.get_timestamp())


def gui_context_from_widget(
    timestamp: int, widget: Gtk.Widget
) -> GUIEnvironmentContext:
    return GUIEnvironmentContext(timestamp, widget.get_screen())


def gui_context_from_timestamp(timestamp: int) -> GUIEnvironmentContext:
    return GUIEnvironmentContext(timestamp, None)


def gui_context_from_keyevent(
    timestamp: int, display: str
) -> GUIEnvironmentContext:
    new_display = GUIEnvironmentContext.ensure_display_open(display)
    screen, *_dummy = new_display.get_pointer()
    return GUIEnvironmentContext(timestamp, screen)


@dataclass
class _InternalData:
    seq: int = 0
    current_event_time: int = 0

    def inc_seq(self) -> None:
        self.seq = self.seq + 1


_internal_data = _InternalData()


def _make_startup_notification_id(time: int) -> str:
    _internal_data.inc_seq()
    return f"kupfer-%{os.getpid()}-{_internal_data.seq}_TIME{time}"


def current_event_time() -> int:
    return int(
        Gtk.get_current_event_time()
        or keybindings.get_current_event_time()
        or _internal_data.current_event_time
    )


def _parse_notify_id(startup_notification_id: str) -> int:
    """Return timestamp or 0 from @startup_notification_id."""
    if "_TIME" in startup_notification_id:
        _ign, bstime = startup_notification_id.split("_TIME", 1)
        with contextlib.suppress(ValueError):
            return abs(int(bstime))

    return 0


@contextlib.contextmanager
def using_startup_notify_id(notify_id: str) -> ty.Any:
    """Pass in a DESKTOP_STARTUP_ID

    with using_startup_notify_id(...) as time:
        pass

    The yelt object is the parsed timestamp
    """
    if timestamp := _parse_notify_id(notify_id):
        Gdk.notify_startup_complete_with_id(notify_id)

    try:
        pretty.print_debug(__name__, "Using startup id", notify_id, timestamp)
        _internal_data.current_event_time = timestamp
        yield timestamp
    finally:
        _internal_data.current_event_time = Gdk.CURRENT_TIME
