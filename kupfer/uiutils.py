"""
User Interface Utility Functions for Kupfer

These helper functions can be called from plugins (are meant to serve this
purpose), but care should be taken to only call UI functions from the main
(default) thread.
"""

import glib
import gtk
import pango

from kupfer import config

def _window_destroy_on_escape(widget, event):
	"""
	Callback function for Window's key press event, will destroy window
	on escape
	"""
	if event.keyval == gtk.gdk.keyval_from_name("Escape"):
		widget.destroy()
		return True

def builder_get_objects_from_file(fname, attrs, autoconnect_to=None):
	"""
	Open @fname with gtk.Builder and yield objects named @attrs

	@fname is sought in the data directories.
	If @autoconnect_to is not None, signals are autoconnected to this object,
	and a user_data object is passed as a namespace containing all @attrs
	"""
	builder = gtk.Builder()
	try:
		import version_subst
	except ImportError:
		package_name = "kupfer"
	else:
		package_name = version_subst.PACKAGE_NAME
	builder.set_translation_domain(package_name)

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
	window.present()

def show_large_type(text):
	"""
	Show @text, large, in a result window.
	"""
	import math
	import textwrap

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

	# Try wrapping a long line
	if (wid > maxwid or hei > maxhei) and len(text.splitlines()) < 2:
		label.set_text(textwrap.fill(text))

	wid, hei = label.size_request()

	if wid > maxwid or hei > maxhei:
		# Round size down to fit inside
		wscale = maxwid * 1.0/wid
		hscale = maxhei * 1.0/hei
		set_font_size(label, math.floor(min(wscale, hscale)*size) or 1.0)

	window.add(label)
	window.set_position(gtk.WIN_POS_CENTER)
	window.set_resizable(False)
	window.connect("key-press-event", _window_destroy_on_escape)
	window.show_all()
