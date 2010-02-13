"""
User Interface Utility Functions for Kupfer

These helper functions can be called from plugins (are meant to serve this
purpose), but care should be taken to only call UI functions from the main
(default) thread.
"""

import glib
import gtk
import pango

from kupfer import pretty
from kupfer import config, version
from kupfer.ui import keybindings

def _window_destroy_on_escape(widget, event):
	"""
	Callback function for Window's key press event, will destroy window
	on escape
	"""
	if event.keyval == gtk.gdk.keyval_from_name("Escape"):
		widget.destroy()
		return True

def _get_current_event_time():
	return gtk.get_current_event_time() or keybindings.get_current_event_time()

def builder_get_objects_from_file(fname, attrs, autoconnect_to=None):
	"""
	Open @fname with gtk.Builder and yield objects named @attrs

	@fname is sought in the data directories.
	If @autoconnect_to is not None, signals are autoconnected to this object,
	and a user_data object is passed as a namespace containing all @attrs
	"""
	builder = gtk.Builder()
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
		builder.connect_signals(autoconnect_to, user_data=names)

def show_text_result(text, title=None):
	"""
	Show @text in a result window.

	Use @title to set a window title
	"""
	class ResultWindowBehavior (object):
		def on_text_result_window_key_press_event(self, widget, event, names):
			return _window_destroy_on_escape(widget, event)

		def on_close_button_clicked(self, widget, names):
			names.text_result_window.window.destroy()
			return True
		def on_copy_button_clicked(self, widget, names):
			clip = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
			textview = names.result_textview
			buf = textview.get_buffer()
			buf.select_range(*buf.get_bounds())
			buf.copy_clipboard(clip)

	window, textview = builder_get_objects_from_file("result.ui",
			("text_result_window", "result_textview"),
			autoconnect_to=ResultWindowBehavior())


	# Set up text buffer
	buf = gtk.TextBuffer()
	buf.set_text(text)
	monospace = gtk.TextTag("fixed")
	monospace.set_property("family", "Monospace")
	monospace.set_property("scale", pango.SCALE_LARGE)
	beg, end = buf.get_bounds()
	tag_table = buf.get_tag_table()
	tag_table.add(monospace)
	buf.apply_tag(monospace, beg, end)

	textview.set_buffer(buf)
	textview.set_wrap_mode(gtk.WRAP_NONE)

	if title:
		window.set_title(title)

	window.show_all()

	# Fix Sizing:
	# We want to size the window so that the
	# TextView is displayed without scrollbars
	# initially, if it fits on screen.
	oldwid, oldhei = textview.window.get_size()
	winwid, winhei = window.get_size()

	max_hsize, max_vsize = window.get_default_size()
	wid, hei = textview.size_request()
	textview.set_wrap_mode(gtk.WRAP_WORD)

	vsize = int(min(hei + (winhei - oldhei) + 5, max_vsize))
	hsize = int(min(wid + (winwid - oldwid) + 5, max_hsize))

	window.resize(hsize, vsize)
	window.present_with_time(_get_current_event_time())

def _wrap_paragraphs(text):
	"""
	Return @text with linewrapped paragraphs
	"""
	import textwrap
	return u"\n\n".join(textwrap.fill(par) for par in text.split("\n\n"))

def show_large_type(text):
	"""
	Show @text, large, in a result window.
	"""
	import math

	text = text.strip()
	window = gtk.Window()
	label = gtk.Label()
	label.set_text(text)

	def set_font_size(label, fontsize=48.0):
		siz_attr = pango.AttrFontDesc(
				pango.FontDescription (str(fontsize)), 0, -1)
		attrs = pango.AttrList()
		attrs.insert(siz_attr)
		label.set_attributes(attrs)
	label.show()

	size = 72.0
	set_font_size(label, size)

	maxwid = gtk.gdk.screen_width() - 50
	maxhei = gtk.gdk.screen_height() - 100
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
	window.set_position(gtk.WIN_POS_CENTER)
	window.set_resizable(False)
	window.set_decorated(False)
	window.set_property("border-width", 10)
	window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
	label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))

	def _window_destroy(widget, event):
		widget.destroy()
		return True
	window.connect("key-press-event", _window_destroy)
	window.show_all()
	window.present_with_time(_get_current_event_time())

SERVICE_NAME = "org.freedesktop.Notifications"
OBJECT_PATH = "/org/freedesktop/Notifications"
IFACE_NAME = "org.freedesktop.Notifications"
def _get_notification_iface():
	"we will activate it over d-bus (start if not running)"
	import dbus
	try:
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object(SERVICE_NAME, OBJECT_PATH)
	except dbus.DBusException, e:
		pretty.print_debug(__name__, e)
		return
	iface_obj = dbus.Interface(proxy_obj, IFACE_NAME)
	return iface_obj

def show_notification(title, text="", icon_name=""):
	notifications = _get_notification_iface()
	if not notifications:
		return None
	rid = notifications.Notify("kupfer", 0, icon_name, title, text, (), {}, -1)
	return rid


