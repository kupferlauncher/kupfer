"""
User Interface Utility Functions for Kupfer

These helper functions can be called from plugins (are meant to serve this
purpose), but care should be taken to only call UI functions from the main
(default) thread.

"""
from __future__ import annotations

import math
import textwrap
import typing as ty

from gi.repository import Gdk, Gtk, Pango

from kupfer import config, version
from kupfer.support import pretty

from . import uievents

if ty.TYPE_CHECKING:
    # commandexec import uiutils TODO: fix imports
    from kupfer.core.commandexec import ExecutionToken

try:
    from typeguard import typeguard_ignore
except ImportError:
    _F = ty.TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:  # pylint: disable=invalid-name
        """This decorator is a noop during static type-checking."""
        return f


def _window_close_on_escape(widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
    """
    Callback function for Window's key press event, will destroy window
    on escape
    """
    if event.keyval == Gdk.keyval_from_name("Escape"):
        widget.close()
        return True

    return False


def builder_get_objects_from_file(
    fname: str, attrs: ty.Iterable[str], autoconnect_to: ty.Any = None
) -> ty.Iterator[ty.Any]:
    """
    Open @fname with Gtk.Builder and yield objects named @attrs

    @fname is sought in the data directories.
    If @autoconnect_to is not None, signals are autoconnected to this object,
    and a user_data object is passed as a namespace containing all @attrs
    """
    builder = Gtk.Builder()
    builder.set_translation_domain(version.PACKAGE_NAME)

    ui_file = config.get_data_file(fname)
    builder.add_from_file(ui_file)

    class Namespace:
        pass

    names = Namespace()
    for attr in attrs:
        obj = builder.get_object(attr)
        setattr(names, attr, obj)
        yield obj

    if autoconnect_to:
        assert hasattr(autoconnect_to, "names")
        autoconnect_to.names = names
        builder.connect_signals(autoconnect_to)  # pylint: disable=no-member


class _ResultWindowBehavior:
    def __init__(self):
        self.names: ty.Any = None

    def on_text_result_window_key_press_event(
        self, widget: Gtk.Widget, event: Gdk.EventKey
    ) -> bool:
        return _window_close_on_escape(widget, event)

    def on_close_button_clicked(self, widget: Gtk.Widget) -> bool:
        self.names.text_result_window.close()
        return True

    def on_copy_button_clicked(self, widget: Gtk.Widget) -> None:
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        textview = self.names.result_textview
        buf = textview.get_buffer()
        buf.select_range(*buf.get_bounds())
        buf.copy_clipboard(clip)


# pylint: disable=too-many-locals
def _calculate_window_size(
    window: Gtk.Window, textview: Gtk.TextView
) -> tuple[int, int]:
    # Find the size of one (monospace) letter
    playout = textview.create_pango_layout("X")
    ink_r, _logical_r = playout.get_pixel_extents()

    # Fix Sizing:
    # We want to size the window so that the
    # TextView is displayed without scrollbars
    # initially, if it fits on screen.
    tw_sr = textview.get_size_request()
    oldwid, oldhei = tw_sr.width, tw_sr.height
    winwid, winhei = window.get_size()

    # max_hsize, max_vsize = window.get_default_size()
    tw_sr = textview.size_request()
    wid, hei = tw_sr.width, tw_sr.height

    # Set max window size to 100 colums x 60 lines
    max_hsize = ink_r.height * 60
    max_vsize = ink_r.width * 100

    vsize = int(min(hei + (winhei - oldhei) + 5, max_vsize))
    hsize = int(min(wid + (winwid - oldwid) + 5, max_hsize))
    return vsize, hsize


@typeguard_ignore
def show_text_result(
    text: str,
    title: str | None = None,
    ctx: "ExecutionToken" | None = None,
) -> None:
    """
    Show @text in a result window.

    Use @title to set a window title
    """

    window, textview = builder_get_objects_from_file(
        "result.ui",
        ("text_result_window", "result_textview"),
        autoconnect_to=_ResultWindowBehavior(),
    )

    # Set up text buffer
    buf = Gtk.TextBuffer()
    buf.set_text(text)
    textview.set_buffer(buf)
    textview.set_wrap_mode(Gtk.WrapMode.NONE)
    textview.set_editable(True)

    if title:
        window.set_title(title)

    if ctx:
        ctx.environment.present_window(window)

    window.show_all()

    hsize, vsize = _calculate_window_size(window, textview)
    textview.set_wrap_mode(Gtk.WrapMode.WORD)
    window.resize(hsize, vsize)
    if ctx:
        ctx.environment.present_window(window)
    else:
        window.present_with_time(uievents.current_event_time())


def _wrap_paragraphs(text: str) -> str:
    """
    Return @text with linewrapped paragraphs
    """
    return "\n\n".join(textwrap.fill(par) for par in text.split("\n\n"))


def _set_font_size(label: Gtk.Label, fontsize: float = 48.0) -> None:
    label.modify_font(Pango.FontDescription.from_string(str(fontsize)))


@typeguard_ignore
def show_large_type(text: str, ctx: "ExecutionToken" | None = None) -> None:
    """
    Show @text, large, in a result window.
    """
    text = text.strip()

    window = Gtk.Window()
    label = Gtk.Label()
    label.set_text(text)
    label.show()

    size = 72.0
    _set_font_size(label, size)

    if ctx:
        screen = ctx.environment.get_screen()
        window.set_screen(screen)  # pylint: disable=no-member
    else:
        screen = Gdk.Screen.get_default()

    maxwid = screen.get_width() - 50
    maxhei = screen.get_height() - 100
    l_sr = label.size_request()  # pylint: disable=no-member
    wid, hei = l_sr.width, l_sr.height

    # If the text contains long lines, we try to
    # hard-wrap the text
    if (wid > maxwid or hei > maxhei) and any(
        len(L) > 100 for L in text.splitlines()
    ):
        label.set_text(_wrap_paragraphs(text))

    l_sr = label.size_request()  # pylint: disable=no-member
    wid, hei = l_sr.width, l_sr.height
    if wid > maxwid or hei > maxhei:
        # Round size down to fit inside
        wscale = maxwid * 1.0 / wid
        hscale = maxhei * 1.0 / hei
        _set_font_size(label, math.floor(min(wscale, hscale) * size) or 1.0)

    window.add(label)  # pylint: disable=no-member
    window.set_position(Gtk.WindowPosition.CENTER)  # pylint: disable=no-member
    window.set_resizable(False)  # pylint: disable=no-member
    window.set_decorated(False)
    window.set_property("border-width", 10)
    # pylint: disable=no-member
    window.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("black"))
    # pylint: disable=no-member
    label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse("white"))

    def _window_destroy(widget, event):
        widget.destroy()
        return True

    window.connect("key-press-event", _window_destroy)
    window.show_all()  # pylint: disable=no-member
    if ctx:
        ctx.environment.present_window(window)
    else:
        window.present_with_time(uievents.current_event_time())


_SERVICE_NAME = "org.freedesktop.Notifications"
_OBJECT_PATH = "/org/freedesktop/Notifications"
_IFACE_NAME = "org.freedesktop.Notifications"


def _get_notification_obj() -> ty.Any:
    "we will activate it over d-bus (start if not running)"
    # pylint: disable=import-outside-toplevel
    import dbus

    try:
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(_SERVICE_NAME, _OBJECT_PATH)
    except dbus.DBusException as exc:
        pretty.print_debug(__name__, exc)
        return None

    return proxy_obj


def show_notification(
    title: str, text: str = "", icon_name: str = "", nid: int = 0
) -> int | None:
    """
    @nid: If not 0, the id of the notification to replace.

    Returns the id of the displayed notification.
    """
    if not (notifications := _get_notification_obj()):
        return None

    hints = {
        "desktop-entry": version.DESKTOP_ID,
    }
    rid = notifications.Notify(
        "kupfer",
        nid,
        icon_name,
        title,
        text,
        (),
        hints,
        -1,
        dbus_interface=_IFACE_NAME,
    )
    return int(rid)
