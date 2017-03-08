"""
User Interface Utility Functions for Kupfer

These helper functions can be called from plugins (are meant to serve this
purpose), but care should be taken to only call UI functions from the main
(default) thread.
"""

from gi.repository import Gtk, Gdk
from gi.repository import Pango

from kupfer import pretty
from kupfer import config, version
from kupfer.ui import uievents

def _window_close_on_escape(widget, event):
    """
    Callback function for Window's key press event, will destroy window
    on escape
    """
    if event.keyval == Gdk.keyval_from_name("Escape"):
        widget.close()
        return True

def builder_get_objects_from_file(fname, attrs, autoconnect_to=None):
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
    class Namespace (object):
        pass
    names = Namespace()
    for attr in attrs:
        obj = builder.get_object(attr)
        setattr(names, attr, obj)
        yield obj
    if autoconnect_to:
        autoconnect_to.names = names
        builder.connect_signals(autoconnect_to)

def show_text_result(text, title=None, ctx=None):
    """
    Show @text in a result window.

    Use @title to set a window title
    """
    class ResultWindowBehavior (object):
        def __init__(self):
            self.names = None

        def on_text_result_window_key_press_event(self, widget, event):
            return _window_close_on_escape(widget, event)

        def on_close_button_clicked(self, widget):
            self.names.text_result_window.close()
            return True
        def on_copy_button_clicked(self, widget):
            clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            textview = self.names.result_textview
            buf = textview.get_buffer()
            buf.select_range(*buf.get_bounds())
            buf.copy_clipboard(clip)

    window, textview = builder_get_objects_from_file("result.ui",
            ("text_result_window", "result_textview"),
            autoconnect_to=ResultWindowBehavior())

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

    # Find the size of one (monospace) letter
    playout = textview.create_pango_layout("X")
    ink_r, logical_r = playout.get_pixel_extents()

    # Fix Sizing:
    # We want to size the window so that the
    # TextView is displayed without scrollbars
    # initially, if it fits on screen.
    tw_sr = textview.get_size_request()
    oldwid, oldhei = tw_sr.width, tw_sr.height
    winwid, winhei = window.get_size()

    #max_hsize, max_vsize = window.get_default_size()
    tw_sr = textview.size_request()
    wid, hei = tw_sr.width, tw_sr.height
    textview.set_wrap_mode(Gtk.WrapMode.WORD)

    # Set max window size to 100 colums x 60 lines
    max_hsize = ink_r.height * 60
    max_vsize = ink_r.width * 100

    vsize = int(min(hei + (winhei - oldhei) + 5, max_vsize))
    hsize = int(min(wid + (winwid - oldwid) + 5, max_hsize))

    window.resize(hsize, vsize)
    if ctx:
        ctx.environment.present_window(window)
    else:
        window.present_with_time(uievents.current_event_time())

def _wrap_paragraphs(text):
    """
    Return @text with linewrapped paragraphs
    """
    import textwrap
    return "\n\n".join(textwrap.fill(par) for par in text.split("\n\n"))

def show_large_type(text, ctx=None):
    """
    Show @text, large, in a result window.
    """
    import math

    text = text.strip()
    window = Gtk.Window()
    label = Gtk.Label()
    label.set_text(text)

    def set_font_size(label, fontsize=48.0):
        siz_attr = Pango.AttrFontDesc(
                Pango.FontDescription.from_string(str(fontsize)), 0, -1)
        attrs = Pango.AttrList()
        attrs.insert(siz_attr)
        label.set_attributes(attrs)
    label.show()

    size = 72.0
    #set_font_size(label, size)

    if ctx:
        screen = ctx.environment.get_screen()
        window.set_screen(screen)
    else:
        screen = Gdk.Screen.get_default()

    maxwid = screen.get_width() - 50
    maxhei = screen.get_height() - 100
    wid, hei = label.size_request()

    # If the text contains long lines, we try to
    # hard-wrap the text
    if ((wid > maxwid or hei > maxhei) and
            any(len(L) > 100 for L in text.splitlines())):
        label.set_text(_wrap_paragraphs(text))

    wid, hei = label.size_request()

    if wid > maxwid or hei > maxhei:
        # Round size down to fit inside
        wscale = maxwid * 1.0/wid
        hscale = maxhei * 1.0/hei
        set_font_size(label, math.floor(min(wscale, hscale)*size) or 1.0)

    window.add(label)
    window.set_position(Gtk.WindowPosition.CENTER)
    window.set_resizable(False)
    window.set_decorated(False)
    window.set_property("border-width", 10)
    window.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("black"))
    label.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse("white"))

    def _window_destroy(widget, event):
        widget.destroy()
        return True
    window.connect("key-press-event", _window_destroy)
    window.show_all()
    if ctx:
        ctx.environment.present_window(window)
    else:
        window.present_with_time(uievents.current_event_time())

SERVICE_NAME = "org.freedesktop.Notifications"
OBJECT_PATH = "/org/freedesktop/Notifications"
IFACE_NAME = "org.freedesktop.Notifications"

def _get_notification_obj():
    "we will activate it over d-bus (start if not running)"
    import dbus
    try:
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
    except dbus.DBusException as e:
        pretty.print_debug(__name__, e)
        return
    return proxy_obj

def show_notification(title, text="", icon_name="", nid=0):
    """
    @nid: If not 0, the id of the notification to replace.

    Returns the id of the displayed notification.
    """
    notifications = _get_notification_obj()
    if not notifications:
        return None
    hints = {
        'desktop-entry': version.DESKTOP_ID,
    }
    rid = notifications.Notify("kupfer",
                               nid, icon_name, title, text, (), hints, -1,
                               dbus_interface=IFACE_NAME)
    return rid


