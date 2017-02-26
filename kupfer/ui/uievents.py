import contextlib
import os

from gi.repository import Gtk, Gdk

from kupfer import pretty
from kupfer.ui import keybindings

def gui_context_from_widget(timestamp, widget):
    return GUIEnvironmentContext(timestamp, widget.get_screen())

def gui_context_from_timestamp(timestamp):
    return GUIEnvironmentContext(timestamp, None)

def gui_context_from_keyevent(timestamp, display):
    new_display = GUIEnvironmentContext.ensure_display_open(display)
    screen, x, y, modifiers = new_display.get_pointer()
    return GUIEnvironmentContext(timestamp, screen)

class GUIEnvironmentContext (object):
    """
    Context object for action execution
    in the current GUI context
    """
    _open_displays = set()

    def __init__(self, timestamp, screen=None):
        self._timestamp = timestamp
        self._screen = screen or Gdk.Screen.get_default()

    def __repr__(self):
        return "<%s time=%r screen=%r>" % (
                type(self).__name__,
                self._timestamp,
                self._screen)

    @classmethod
    def ensure_display_open(cls, display):
        """
        Return GdkDisplay for name @display.

        Return default if @display is None.
        """
        return Gdk.DisplayManager.get().get_default_display()
        def norm_name(name):
            "normalize display name"
            if name[-2] == ":":
                return name+".0"
            return name
        dm = Gdk.display_manager_get()
        if display:
            new_display = None
            for disp in dm.list_displays():
                if norm_name(disp.get_name()) == norm_name(display):
                    new_display = disp
                    break
            if new_display is None:
                pretty.print_debug(__name__,
                        "Opening display in ensure_display_open", display)
                new_display = Gdk.Display(display)
        else:
            new_display = Gdk.Display.get_default()
        ## Hold references to all open displays
        cls._open_displays = set(dm.list_displays())
        return new_display

    @classmethod
    def _try_close_unused_displays(cls, screen):
        """@screen is current GdkScreen

        Try to close inactive displays...
        Take all GtkWindow that are hidden, and move to the
        current screen. If no windows remain then we close
        the display, but we never close the default display.
        """
        def debug(*x):
            pretty.print_debug(__name__, *x)
        display = screen.get_display()
        dm = Gdk.DisplayManager.get()
        for disp in list(dm.list_displays()):
            if disp != display and disp != Gdk.Display.get_default():
                debug("Trying to close", disp.get_name())
                open_windows = 0
                for window in Gtk.window_list_toplevels():
                    # find windows on @disp
                    if window.get_screen().get_display() != disp:
                        continue
                    if not window.get_property("visible"):
                        debug("Moving window", window.get_name())
                        debug("Moving", window.get_title())
                        window.set_screen(screen)
                    else:
                        debug("Open window blocks close")
                        open_windows += 1
                if not open_windows:
                    debug("Closing display", disp.get_name())
                    disp.close()


    def get_timestamp(self):
        return self._timestamp

    def get_startup_notification_id(self):
        """
        Always returns a byte string
        """
        return _make_startup_notification_id(self.get_timestamp())

    def get_display(self):
        """return the display name to show new windows on

        Always returns a byte string
        """
        return self._screen.make_display_name()

    def get_screen(self):
        return self._screen

    def present_window(self, window):
        """
        Show and present @window on the current
        workspace, screen & display as appropriate.

        @window: A Gtk.Window
        """
        window.set_screen(self.get_screen())
        window.present_with_time(self.get_timestamp())

class _internal_data (object):
    seq = 0
    current_event_time = 0

    @classmethod
    def inc_seq(cls):
        cls.seq = cls.seq + 1

def _make_startup_notification_id(time):
    _internal_data.inc_seq()
    return "%s-%d-%s_TIME%d" % ("kupfer", os.getpid(), _internal_data.seq, time)

def current_event_time():
    return (Gtk.get_current_event_time() or
            keybindings.get_current_event_time() or
            _internal_data.current_event_time)

def _parse_notify_id(startup_notification_id):
    """
    Return timestamp or 0 from @startup_notification_id
    """
    time = 0
    if "_TIME" in startup_notification_id:
        _ign, bstime = startup_notification_id.split("_TIME", 1)
        try:
            time = abs(int(bstime))
        except ValueError:
            pass
    return time

@contextlib.contextmanager
def using_startup_notify_id(notify_id):
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
        pretty.print_debug(__name__, "Using startup id", repr(notify_id), timestamp)
        _internal_data.current_event_time = timestamp
        yield timestamp
    finally:
        _internal_data.current_event_time = Gdk.CURRENT_TIME

