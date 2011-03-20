__kupfer_name__ = _("Quick Image Viewer")
__kupfer_actions__ = ("View", )
__description__ = ""
__version__ = ""
__author__ = ""

import shutil

import gio
import glib
import gtk

from kupfer.objects import Action, FileLeaf
from kupfer.objects import OperationError
from kupfer import utils

def is_content_type(fileleaf, ctype):
	predicate = gio.content_type_is_a
	ctype_guess, uncertain = gio.content_type_guess(fileleaf.object, None, True)
	ret = predicate(ctype_guess, ctype)
	if ret or not uncertain:
		return ret
	content_attr = gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
	gfile = gio.File(fileleaf.object)
	if not gfile.query_exists(None):
		return
	info = gfile.query_info(content_attr)
	content_type = info.get_attribute_string(content_attr)
	return predicate(content_type, ctype)

def _set_size(loader, width, height, max_w, max_h):
	if width <= max_w and height <= max_h:
		return
	w_scale = max_w*1.0/width
	h_scale = max_h*1.0/height
	scale = min(w_scale, h_scale)
	loader.set_size(int(width*scale), int(height*scale))

def load_image_max_size(filename, w, h):
	pl = gtk.gdk.PixbufLoader()
	pl.connect("size-prepared", _set_size, w, h)
	try:
		with open(filename, "r") as f:
			shutil.copyfileobj(f, pl)
		pl.close()
	except (glib.GError, EnvironmentError) as exc:
		raise OperationError(exc)
	return pl.get_pixbuf()

def window_key_press(window, event, filepath):
	if gtk.gdk.keyval_name(event.keyval) == "Escape":
		window.destroy()
		return True
	if gtk.gdk.keyval_name(event.keyval) == "Return":
		utils.show_path(filepath)
		window.destroy()
		return True

class View (Action):
	def __init__(self):
		Action.__init__(self, _("View Image"))

	def item_types(self):
		yield FileLeaf

	def valid_for_item(self, obj):
		return is_content_type(obj, "image/*")

	def activate(self, obj):
		image_widget = gtk.Image()
		h = gtk.gdk.screen_height()
		w = gtk.gdk.screen_width()
		image_widget.set_from_pixbuf(load_image_max_size(obj.object, w, h))
		image_widget.show()
		window = gtk.Window() 
		window.set_title(utils.get_display_path_for_bytestring(obj.object))
		window.set_position(gtk.WIN_POS_CENTER)
		window.add(image_widget)
		window.present()
		window.connect("key-press-event", window_key_press, obj.object)

	def get_description(self):
		return None

