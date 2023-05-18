__kupfer_name__ = _("Quick Image Viewer")
__kupfer_actions__ = ("View",)
__description__ = ""
__version__ = ""
__author__ = ""

import shutil
import typing as ty

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from kupfer import launch
from kupfer.obj import Action, FileLeaf, OperationError

if ty.TYPE_CHECKING:
    from gettext import gettext as _


def _on_size_prepared(loader, width, height, max_w, max_h):
    if width <= max_w and height <= max_h:
        return

    w_scale = max_w * 1.0 / width
    h_scale = max_h * 1.0 / height
    scale = min(w_scale, h_scale)
    loader.set_size(int(width * scale), int(height * scale))


def load_image_max_size(
    filename: str, width: int, height: int
) -> GdkPixbuf.Pixbuf:
    pbloader = GdkPixbuf.PixbufLoader()
    pbloader.connect("size-prepared", _on_size_prepared, width, height)
    try:
        with open(filename, "rb") as fin:
            shutil.copyfileobj(fin, pbloader)

        pbloader.close()

    except (GLib.GError, OSError) as exc:
        raise OperationError(exc) from exc

    return pbloader.get_pixbuf()


class View(Action):
    def __init__(self):
        Action.__init__(self, _("View Image"))
        self.open_windows = {}

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return leaf.is_content_type("image/*")

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        ## If the same file @obj is already open,
        ## then close its window.
        if leaf.object in self.open_windows:
            open_window = self.open_windows.pop(leaf.object)
            open_window.destroy()
            return

        image_widget = Gtk.Image()
        image_widget.set_from_pixbuf(
            load_image_max_size(
                leaf.object, Gdk.Screen.height(), Gdk.Screen.width()
            )
        )
        image_widget.show()

        window = Gtk.Window()
        window.set_title(str(leaf))
        # pylint: disable=no-member
        window.set_position(Gtk.WindowPosition.CENTER)
        # pylint: disable=no-member
        window.add(image_widget)
        ctx.environment.present_window(window)
        window.connect(
            "key-press-event", self._on_window_key_press, leaf.object
        )
        window.connect("delete-event", self._on_window_deleted, leaf.object)
        self.open_windows[leaf.object] = window

    def _on_window_deleted(self, window, event, filename):
        self.open_windows.pop(filename, None)
        return False

    def _on_window_key_press(self, window, event, filepath):
        if Gdk.keyval_name(event.keyval) == "Escape":
            self._on_window_deleted(window, event, filepath)
            window.destroy()
            return True

        if Gdk.keyval_name(event.keyval) == "Return":
            self._on_window_deleted(window, event, filepath)
            launch.show_path(filepath)
            window.destroy()
            return True

        return False

    def get_description(self):
        return None
