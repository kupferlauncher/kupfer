from __future__ import annotations

import contextlib
import os
import typing as ty

from gi.repository import Gdk, Gtk

from kupfer.support import pretty
from kupfer.ui import keybindings


def try_close_unused_displays(screen: Gdk.Screen) -> None:
    """@screen is current GdkScreen

    Try to close inactive displays...
    Take all GtkWindow that are hidden, and move to the
    current screen. If no windows remain then we close
    the display, but we never close the default display.
    """
    skip_displays = (screen.get_display(), Gdk.Display.get_default())
    dmgr = Gdk.DisplayManager.get()
    for disp in dmgr.list_displays():
        if disp in skip_displays:
            continue

        pretty.print_debug(__name__, "Trying to close", disp.get_name())
        open_windows = 0
        for window in Gtk.window_list_toplevels():
            # find windows on @disp
            if window.get_screen().get_display() != disp:
                continue

            if not window.get_property("visible"):
                pretty.print_debug(__name__, "Moving window", window.get_name())
                pretty.print_debug(__name__, "Moving", window.get_title())
                window.set_screen(screen)
            else:
                pretty.print_debug(__name__, "Open window blocks close")
                open_windows += 1

        if not open_windows:
            pretty.print_debug(__name__, "Closing display", disp.get_name())
            disp.close()


class GUIEnvironmentContext:
    """
    Context object for action execution
    in the current GUI context
    """

    def __init__(self, timestamp: int, screen: Gdk.Screen | None = None):
        self._timestamp = timestamp
        self._screen: ty.Optional[Gdk.Screen] = (
            screen or Gdk.Screen.get_default()
        )

    def __repr__(self):
        return (
            f"<{type(self).__name__} "
            f"time={self._timestamp!r} screen={self._screen!r}>"
        )

    @classmethod
    def ensure_display_open(cls, _display: Gdk.Display | None) -> Gdk.Display:
        """
        Return GdkDisplay for name @display.

        Return default if @display is None.
        """
        return Gdk.DisplayManager.get().get_default_display()

    def get_timestamp(self) -> int:
        return self._timestamp

    def get_startup_notification_id(self) -> str:
        """
        Always returns a byte string
        """
        return _make_startup_notification_id(self.get_timestamp())

    def get_display(self) -> str:
        """return the display name to show new windows on

        Always returns a byte string
        """
        return self._screen.make_display_name()  # type: ignore

    def get_screen(self) -> Gdk.Screen | None:
        return self._screen

    def present_window(self, window: Gtk.Window) -> None:
        """
        Show and present @window on the current
        workspace, screen & display as appropriate.

        @window: A Gtk.Window
        """
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


class _InternalData:
    seq = 0
    current_event_time = 0

    @classmethod
    def inc_seq(cls) -> None:
        cls.seq = cls.seq + 1


def _make_startup_notification_id(time: int) -> str:
    _InternalData.inc_seq()
    return f"kupfer-%{os.getpid()}-{_InternalData.seq}_TIME{time}"


def current_event_time() -> int:
    return int(
        Gtk.get_current_event_time()
        or keybindings.get_current_event_time()
        or _InternalData.current_event_time
    )


def _parse_notify_id(startup_notification_id: str) -> int:
    """
    Return timestamp or 0 from @startup_notification_id
    """
    timestamp = 0
    if "_TIME" in startup_notification_id:
        _ign, bstime = startup_notification_id.split("_TIME", 1)
        with contextlib.suppress(ValueError):
            timestamp = abs(int(bstime))

    return timestamp


@contextlib.contextmanager
def using_startup_notify_id(notify_id: str) -> ty.Any:
    """
    Pass in a DESKTOP_STARTUP_ID

    with using_startup_notify_id(...) as time:
        pass

    The yelt object is the parsed timestamp
    """
    timestamp = _parse_notify_id(notify_id)
    if timestamp:
        Gdk.notify_startup_complete_with_id(notify_id)
    try:
        pretty.print_debug(
            __name__, "Using startup id", repr(notify_id), timestamp
        )
        _InternalData.current_event_time = timestamp
        yield timestamp
    finally:
        _InternalData.current_event_time = Gdk.CURRENT_TIME
