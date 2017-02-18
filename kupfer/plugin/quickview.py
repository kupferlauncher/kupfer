__kupfer_name__ = _("Quick Image Viewer")
__kupfer_actions__ = ("View", )
__description__ = ""
__version__ = ""
__author__ = ""

import shutil

from gi.repository import Gio, Gdk, GLib
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from kupfer.objects import Action, FileLeaf
from kupfer.objects import OperationError
from kupfer import utils


def _set_size(loader, width, height, max_w, max_h):
    if width <= max_w and height <= max_h:
        return
    w_scale = max_w*1.0/width
    h_scale = max_h*1.0/height
    scale = min(w_scale, h_scale)
    loader.set_size(int(width*scale), int(height*scale))

def load_image_max_size(filename, w, h):
    pl = GdkPixbuf.PixbufLoader()
    pl.connect("size-prepared", _set_size, w, h)
    try:
        with open(filename, "rb") as f:
            shutil.copyfileobj(f, pl)
        pl.close()
    except (GLib.GError, EnvironmentError) as exc:
        raise OperationError(exc)
    return pl.get_pixbuf()

class View (Action):
    def __init__(self):
        Action.__init__(self, _("View Image"))
        self.open_windows = {}

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, obj):
        return obj.is_content_type("image/*")

    def wants_context(self):
        return True

    def activate(self, obj, ctx):
        ## If the same file @obj is already open,
        ## then close its window.
        if obj.object in self.open_windows:
            open_window = self.open_windows.pop(obj.object)
            open_window.destroy()
            return
        image_widget = Gtk.Image()
        h = Gdk.Screen.height()
        w = Gdk.Screen.width()
        image_widget.set_from_pixbuf(load_image_max_size(obj.object, w, h))
        image_widget.show()
        window = Gtk.Window() 
        window.set_title(str(obj))
        window.set_position(Gtk.WindowPosition.CENTER)
        window.add(image_widget)
        ctx.environment.present_window(window)
        window.connect("key-press-event", self.window_key_press, obj.object)
        window.connect("delete-event", self.window_deleted, obj.object)
        self.open_windows[obj.object] = window

    def window_deleted(self, window, event, filename):
        self.open_windows.pop(filename, None)
        return False

    def window_key_press(self, window, event, filepath):
        if Gdk.keyval_name(event.keyval) == "Escape":
            self.window_deleted(window, event, filepath)
            window.destroy()
            return True
        if Gdk.keyval_name(event.keyval) == "Return":
            self.window_deleted(window, event, filepath)
            utils.show_path(filepath)
            window.destroy()
            return True

    def get_description(self):
        return None

