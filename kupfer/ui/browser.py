# -*- coding: UTF-8 -*-

import io
import itertools
import signal
import sys
import textwrap
import time

import gtk
import gio
import gobject
import cairo

from kupfer import kupferui
from kupfer import version

from kupfer import scheduler
from kupfer.ui import accelerators
from kupfer.ui import keybindings
from kupfer.ui import listen
from kupfer.ui import uievents
from kupfer.core import data, relevance, learn
from kupfer.core import settings
from kupfer import icons
from kupfer import interface
from kupfer import pretty


_escape_table = {
		ord(u"&"): u"&amp;",
		ord(u"<"): u"&lt;",
		ord(u">"): u"&gt;",
	}

def tounicode(ustr):
	if isinstance(ustr, unicode):
		return ustr
	return ustr.decode("UTF-8", "replace")

def escape_markup_str(mstr):
	"""
	Use a simeple homegrown replace table to replace &, <, > with
	entities in @mstr
	"""
	return tounicode(mstr).translate(_escape_table)

def text_direction_is_ltr():
	return gtk.widget_get_default_direction() != gtk.TEXT_DIR_RTL

def make_rounded_rect(cr,x,y,width,height,radius):
	"""
	Draws a rounded rectangle with corners of @radius
	"""
	MPI = 3.1415926535897931
	cr.save()

	w,h = width, height

	cr.move_to(radius, 0)
	cr.line_to(w-radius,0)
	cr.arc(w-radius, radius, radius, 3*MPI/2, 2*MPI)
	cr.line_to(w, h-radius)
	cr.arc(w-radius, h-radius, radius, 0, MPI/2)
	cr.line_to(radius, h)
	cr.arc(radius, h-radius, radius, MPI/2, MPI)
	cr.line_to(0, radius)
	cr.arc(radius, radius, radius, MPI, 3*MPI/2)
	cr.close_path()
	cr.restore()

def get_glyph_pixbuf(text, sz, center_vert=True, color=None):
	"""Return pixbuf for @text

	if @center_vert, then center completely vertically
	"""
	margin = sz * 0.1
	ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, sz, sz)
	cc = cairo.Context(ims)

	cc.move_to(margin, sz-margin)
	cc.set_font_size(sz/2)
	if color is None:
		cc.set_source_rgba(0,0,0,1)
	else:
		cc.set_source_rgb(*color)

	cc.text_path(text)
	x1, y1, x2, y2 =cc.path_extents()
	skew_horiz = ((sz-x2) - (x1))/2.0
	skew_vert = ((sz-y2) - (y1))/2.0
	if not center_vert:
		skew_vert = skew_vert*0.2 - margin*0.5
	cc.new_path()
	cc.move_to(margin+skew_horiz, sz-margin+skew_vert)
	cc.text_path(text)
	cc.fill()

	ims.flush()
	f = io.BytesIO()
	ims.write_to_png(f)

	loader = gtk.gdk.PixbufLoader()
	loader.write(f.getvalue())
	loader.close()

	return loader.get_pixbuf()


# State Constants
class State (object):
	Wait, Match, NoMatch = (1,2,3)

class LeafModel (object):
	"""A base for a tree view
	With a magic load-on-demand feature.

	self.set_base will set its base iterator
	and self.populate(num) will load @num items into
	the model
	"""
	def __init__(self):
		"""
		First column is always the object -- returned by get_object
		it needs not be specified in columns
		"""
		columns = (gobject.TYPE_OBJECT, str, str, str)
		self.store = gtk.ListStore(gobject.TYPE_PYOBJECT, *columns)
		self.object_column = 0
		self.base = None
		self._setup_columns()

	def __len__(self):
		return len(self.store)

	def _setup_columns(self):
		self.icon_col = 1
		self.val_col = 2
		self.info_col = 3
		self.rank_col = 4

		# only show in debug mode
		show_rank_col = pretty.debug

		from pango import ELLIPSIZE_MIDDLE
		cell = gtk.CellRendererText()
		cell.set_property("ellipsize", ELLIPSIZE_MIDDLE)
		cell.set_property("width-chars", 45)
		col = gtk.TreeViewColumn("item", cell)

		"""
		info_cell = gtk.CellRendererPixbuf()
		info_cell.set_property("height", 16)
		info_cell.set_property("width", 16)
		info_col = gtk.TreeViewColumn("info", info_cell)
		info_col.add_attribute(info_cell, "icon-name", self.info_col)
		"""
		info_cell = gtk.CellRendererText()
		info_cell.set_property("width-chars", 1)
		info_col = gtk.TreeViewColumn("info", info_cell)
		info_col.add_attribute(info_cell, "text", self.info_col)

		col.add_attribute(cell, "markup", self.val_col)

		nbr_cell = gtk.CellRendererText()
		nbr_col = gtk.TreeViewColumn("rank", nbr_cell)
		nbr_cell.set_property("width-chars", 3)
		nbr_col.add_attribute(nbr_cell, "text", self.rank_col)

		icon_cell = gtk.CellRendererPixbuf()
		#icon_cell.set_property("height", 32)
		#icon_cell.set_property("width", 32)
		#icon_cell.set_property("stock-size", gtk.ICON_SIZE_LARGE_TOOLBAR)

		icon_col = gtk.TreeViewColumn("icon", icon_cell)
		icon_col.add_attribute(icon_cell, "pixbuf", self.icon_col)

		self.columns = [icon_col, col, info_col,]
		if show_rank_col:
			self.columns += (nbr_col, )

	def _get_column(self, treepath, col):
		iter = self.store.get_iter(treepath)
		val = self.store.get_value(iter, col)
		return val

	def get_object(self, path):
		return self._get_column(path, self.object_column)

	def get_store(self):
		return self.store

	def clear(self):
		"""Clear the model and reset its base"""
		self.store.clear()
		self.base = None

	def set_base(self, baseiter):
		self.base = iter(baseiter)

	def populate(self, num=None):
		"""
		populate model with num items from its base
		and return first item inserted
		if num is none, insert everything
		"""
		if not self.base:
			return None
		if num:
			iterator = itertools.islice(self.base, num)
		first = None
		for item in iterator:
			self.add(item)
			if not first: first = item.object
		# first.object is a leaf
		return first

	def _get_row(self, rankable):
		"""Use the UI description functions get_*
		to initialize @rankable into the model
		"""
		leaf, rank = rankable.object, rankable.rank
		icon = self.get_icon(leaf)
		markup = self.get_label_markup(rankable)
		info = self.get_aux_info(leaf)
		rank_str = self.get_rank_str(rank)
		return (rankable, icon, markup, info, rank_str)

	def add(self, rankable):
		self.store.append(self._get_row(rankable))

	def add_first(self, rankable):
		self.store.prepend(self._get_row(rankable))

	def get_icon_size(self):
		return gtk.icon_size_lookup(gtk.icon_size_from_name("kupfer-small"))[0]

	def get_icon(self, leaf):
		sz = self.get_icon_size()
		if sz >= 8:
			return leaf.get_thumbnail(sz, sz) or leaf.get_pixbuf(sz)

	def get_label_markup(self, rankable):
		leaf = rankable.object
		# Here we use the items real name
		# Previously we used the alias that was matched,
		# but it can be too confusing or ugly
		name = escape_markup_str(unicode(leaf))
		desc = escape_markup_str(leaf.get_description() or "")
		if desc:
			text = u'%s\n<small>%s</small>' % (name, desc, )
		else:
			text = u'%s' % (name, )
		return text

	def get_aux_info(self, leaf):
		# info: display arrow if leaf has content
		fill_space = u"\N{EM SPACE}"
		if text_direction_is_ltr():
			content_mark = u"\N{BLACK RIGHT-POINTING SMALL TRIANGLE}"
		else:
			content_mark = u"\N{BLACK LEFT-POINTING SMALL TRIANGLE}"

		info = u""
		if learn.is_favorite(leaf):
			info += u"\N{BLACK STAR}"
		else:
			info += fill_space
		if hasattr(leaf, "has_content") and leaf.has_content():
			info += content_mark
		return info
	def get_rank_str(self, rank):
		# Display rank empty instead of 0 since it looks better
		return str(int(rank)) if rank else ""

class MatchView (gtk.Bin):
	"""
	A Widget for displaying name, icon and underlining properly if
	it matches
	"""
	__gtype_name__ = "MatchView"

	def __init__(self):
		gobject.GObject.__init__(self)
		# object attributes
		self.label_char_width = 25
		self.preedit_char_width = 5
		self.match_state = State.Wait

		self.object_stack = []

		self.connect("realize", self._update_theme)
		self.connect("style-set", self._update_theme)
		# finally build widget
		self.build_widget()
		self.cur_icon = None
		self.cur_text = None
		self.cur_match = None

	@property
	def icon_size(self):
		return gtk.icon_size_lookup(gtk.icon_size_from_name("kupfer-large"))[0]

	def _update_theme(self, *args):
		# Style subtables to choose from
		# fg, bg, text, base
		# light, mid, dark

		# Use a darker color for selected state
		# leave active state as preset
		selectedc = self.style.dark[gtk.STATE_SELECTED]
		self.event_box.modify_bg(gtk.STATE_SELECTED, selectedc)

	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""
		from pango import ELLIPSIZE_MIDDLE
		self.label = gtk.Label("<match>")
		self.label.set_single_line_mode(True)
		self.label.set_width_chars(self.label_char_width)
		self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
		self.icon_view = gtk.Image()

		# infobox: icon and match name
		icon_align = gtk.Alignment(0.5, 0.5, 0, 0)
		icon_align.set_property("top-padding", 5)
		icon_align.add(self.icon_view)
		infobox = gtk.HBox()
		infobox.pack_start(icon_align, True, True, 0)
		box = gtk.VBox()
		box.pack_start(infobox, True, False, 0)
		self._editbox = gtk.HBox()
		self._editbox.pack_start(self.label, True, True, 0)
		box.pack_start(self._editbox, False, True, 0)
		self.event_box = gtk.EventBox()
		self.event_box.add(box)
		self.event_box.connect("expose-event", self._box_expose)
		self.event_box.set_app_paintable(True)
		self.add(self.event_box)
		self.event_box.show_all()
		self.__child = self.event_box

	def _box_expose(self, widget, event):
		"Draw background on the EventBox"
		rect = widget.get_allocation()
		context = widget.window.cairo_create()
		# set a clip region for the expose event
		context.rectangle(event.area.x, event.area.y,
		                  event.area.width, event.area.height)
		scale = 1.0/2**16
		# paint over GtkEventBox's default background
		context.clip_preserve()
		context.set_operator(cairo.OPERATOR_SOURCE)
		normc = widget.style.bg[gtk.STATE_NORMAL]
		toplevel_window = widget.get_toplevel()
		if toplevel_window.is_composited():
			opacity = 0.01*toplevel_window.style_get_property('opacity')
			context.set_source_rgba(normc.red*scale,
					normc.green*scale, normc.blue*scale, opacity)
		else:
			context.set_source_rgba(normc.red*scale,
					normc.green*scale, normc.blue*scale, 1.0)
		context.fill()

		radius = self.style_get_property('corner-radius')
		make_rounded_rect(context, 0, 0, rect.width, rect.height, radius=radius)
		# Get the current selection color
		newc = widget.style.bg[widget.get_state()]
		context.set_operator(cairo.OPERATOR_SOURCE)
		opacity = 0.01*self.style_get_property('opacity')
		context.set_source_rgba(newc.red*scale,
				newc.green*scale, newc.blue*scale, opacity)
		context.fill()
		return False

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)

	def _render_composed_icon(self, base, pixbufs, small_size):
		"""
		Render the main selection + a string of objects on the stack.

		Scale the main image into the upper portion, leaving a clear
		strip at the bottom where we line up the small icons.

		@base: main selection pixbuf
		@pixbufs: icons of the object stack, in final (small) size
		@small_size: the size of the small icons
		"""
		sz = self.icon_size
		base_scale = min((sz-small_size)*1.0/base.get_height(),
				sz*1.0/base.get_width())
		new_sz_x = int(base_scale*base.get_width())
		new_sz_y = int(base_scale*base.get_height())
		if not base.get_has_alpha():
			base = base.add_alpha(False, 0, 0, 0)
		destbuf = base.scale_simple(sz, sz, gtk.gdk.INTERP_NEAREST)
		destbuf.fill(0x00000000)
		# Align in the middle of the area
		offset_x = (sz - new_sz_x)/2
		offset_y = ((sz - small_size) - new_sz_y)/2
		base.composite(destbuf, offset_x, offset_y, new_sz_x, new_sz_y,
				offset_x, offset_y,
				base_scale, base_scale, gtk.gdk.INTERP_BILINEAR, 255)

		# @fr is the scale compared to the destination pixbuf
		fr = small_size*1.0/sz
		dest_y = offset_y = int((1-fr)*sz)
		for idx, pbuf in enumerate(pixbufs):
			dest_x = offset_x = int(fr*sz)*idx
			pbuf.copy_area(0,0, small_size,small_size, destbuf, dest_x,dest_y)
		return destbuf

	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		# update icon
		icon = self.cur_icon
		if icon:
			if self.match_state is State.NoMatch:
				icon = self._dim_icon(icon)
			if icon and self.object_stack:
				small_max = 6
				small_size = 16
				pixbufs = [o.get_pixbuf(small_size) for o in
						self.object_stack[-small_max:]]
				icon = self._render_composed_icon(icon, pixbufs, small_size)
			self.icon_view.set_from_pixbuf(icon)
		else:
			self.icon_view.set_from_icon_name("gtk-file", self.icon_size)
			self.icon_view.set_pixel_size(self.icon_size)

		if not self.cur_text:
			self.label.set_text("<no text>")
			return

		if not self.cur_match:
			if self.match_state is not State.Match:
				# Allow markup in the text string if we have no match
				self.label.set_markup(self.cur_text)
			else:
				self.label.set_text(self.cur_text)
			return

		# update the text label
		text = unicode(self.cur_text)
		key = unicode(self.cur_match).lower()

		format_match=(lambda m: u"<u><b>%s</b></u>" % escape_markup_str(m))
		markup = relevance.formatCommonSubstrings(text, key,
				format_clean=escape_markup_str,
				format_match=format_match)

		self.label.set_markup(markup)

	@classmethod
	def _dim_icon(cls, icon):
		if icon:
			dim_icon = icon.copy()
			icon.saturate_and_pixelate(dim_icon, 0, True)
		else:
			dim_icon = None
		return dim_icon

	def set_object(self, text, icon, update=True):
		self.cur_text = text
		self.cur_icon = icon
		if update:
			self.update_match()

	def set_match(self, match=None, state=None, update=True):
		self.cur_match = match
		if state:
			self.match_state = state
		else:
			self.match_state = (State.NoMatch, State.Match)[self.cur_match != None]
		if update:
			self.update_match()

	def set_match_state(self, text, icon, match=None, state=None, update=True):
		self.set_object(text,icon, update=False)
		self.set_match(match, state, update=False)
		if update:
			self.update_match()

	def set_match_text(self, text, update=True):
		self.cur_match = text
		if update:
			self.update_match()

	def expand_preedit(self, preedit):
		new_label_width = self.label_char_width - self.preedit_char_width
		self.label.set_width_chars(new_label_width)
		preedit.set_width_chars(self.preedit_char_width)
		pass

	def shrink_preedit(self, preedit):
		self.label.set_width_chars(self.label_char_width)
		preedit.set_width_chars(0)
		pass

	def inject_preedit(self, preedit):
		"""
		@preedit: Widget to be injected or None
		"""
		if preedit:
			old_parent = preedit.get_parent()
			if old_parent:
				old_parent.remove(preedit)
			self.shrink_preedit(preedit)
			self._editbox.pack_start(preedit, False, True, 0)
			selectedc = self.style.dark[gtk.STATE_SELECTED]
			preedit.modify_bg(gtk.STATE_SELECTED, selectedc)
			preedit.show()
			preedit.grab_focus()
		else:
			self.label.set_width_chars(self.label_char_width)
			self.label.set_alignment(.5,.5)

gobject.type_register(MatchView)
gtk.widget_class_install_style_property(MatchView,
		('corner-radius', gobject.TYPE_INT, 'Corner radius',
		 'Radius of bezel around match',
		 0, 50, 15,
		 gobject.PARAM_READABLE))
gtk.widget_class_install_style_property(MatchView,
		('opacity', gobject.TYPE_INT, 'Bezel opacity',
		 'Opacity of bezel around match',
		 50, 100, 95,
		 gobject.PARAM_READABLE))

class Search (gtk.Bin):
	"""
	A Widget for displaying search results
	icon + aux table etc

	Signals
	* cursor-changed: def callback(widget, selection)
		called with new selected (represented) object or None
	* activate: def callback(widget, selection)
		called with activated leaf, when the widget is activated
		by double-click in table
	* table-event: def callback(widget, table, event)
		called when the user types in the table
	"""
	__gtype_name__ = 'Search'
	def __init__(self):
		gobject.GObject.__init__(self)
		# object attributes
		self.model = LeafModel()
		self.match = None
		self.match_state = State.Wait
		self.text = u""
		# internal constants
		self.show_initial = 10
		self.show_more = 10
		# number rows to skip when press PgUp/PgDown
		self.page_step = 7
		self.source = None
		self._old_win_position=None
		self._has_search_result = False
		self._initialized = False
		# finally build widget
		self.build_widget()
		self.icon_size = None
		self.on_style_set()
		self.setup_empty()
		self.connect("style-set", self.on_style_set)

	def on_style_set(self, *args):
		self.icon_size = \
			gtk.icon_size_lookup(gtk.icon_size_from_name("kupfer-large"))[0]

	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""
		self.match_view = MatchView()

		self.table = gtk.TreeView(self.model.get_store())
		self.table.set_headers_visible(False)
		self.table.set_property("enable-search", False)

		for col in self.model.columns:
			self.table.append_column(col)

		self.table.connect("row-activated", self._row_activated)
		self.table.connect("cursor-changed", self._cursor_changed)

		self.scroller = gtk.ScrolledWindow()
		self.scroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		self.scroller.add(self.table)
		vscroll = self.scroller.get_vscrollbar()
		vscroll.connect("change-value", self._table_scroll_changed)

		self.list_window = gtk.Window(gtk.WINDOW_POPUP)
		self.list_window.set_name("kupfer-list")

		box = gtk.VBox()
		box.pack_start(self.match_view, True, True, 0)
		self.add(box)
		box.show_all()
		self.__child = box

		self.list_window.add(self.scroller)
		self.scroller.show_all()

	def get_current(self):
		"""
		return current selection
		"""
		return self.match

	def set_object_stack(self, stack):
		self.match_view.object_stack[:] = stack
		self.match_view.update_match()

	def set_source(self, source):
		"""Set current source (to get icon, name etc)"""
		self.source = source

	def get_match_state(self):
		return self.match_state
	def get_match_text(self):
		return self.text

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)

	def get_table_visible(self):
		return self.list_window.get_property("visible")

	def hide_table(self):
		self.list_window.hide()

	def _show_table(self):
		table_maxlen = self.style_get_property('list-length')
		opacity = 0.01*self.style_get_property('list-opacity')
		# self.window is a GdkWindow (of self's parent)
		win_width, win_height = self.window.get_size()
		pos_x, pos_y = self.window.get_position()
		# find origin in parent's coordinates
		self_x, self_y = self.translate_coordinates(self.get_parent(), 0, 0)
		self_width = self.size_request()[0]
		sub_x = pos_x
		sub_y = pos_y + win_height
		table_w, table_len = self.table.size_request()
		subwin_height = min(table_len, table_maxlen) or 100
		subwin_width = self_width*2 - self_x
		if not text_direction_is_ltr():
			sub_x += win_width - subwin_width + self_x
		else:
			sub_x -= self_x
		self.list_window.move(sub_x, sub_y)
		self.list_window.resize(subwin_width, subwin_height)

		win = self.get_toplevel()
		self.list_window.set_transient_for(win)
		self.list_window.set_property("focus-on-map", False)
		self.list_window.set_opacity(opacity)
		self.list_window.show()
		self._old_win_position = pos_x, pos_y

	def show_table(self):
		self.go_down(True)

	def _table_scroll_changed(self, scrollbar, scroll_type, value):
		"""When the scrollbar changes due to user interaction"""
		# page size: size of currently visible area
		adj = scrollbar.get_adjustment()
		upper = adj.get_property("upper")
		page_size = adj.get_property("page-size")

		if value + page_size >= upper:
			self.populate(self.show_more)

	# table methods
	def _table_set_cursor_at_row(self, row):
		path_at_row = lambda r: (r,)
		self.table.set_cursor(path_at_row(row))

	def go_up(self, rows_count=1):
		"""
		Upwards in the table
		"""
		row_at_path = lambda p: p[0]

		# go up, simply. close table if we go up from row 0
		path, col = self.table.get_cursor()
		if path:
			r = row_at_path(path)
			if r >= 1:
				self._table_set_cursor_at_row(r-min(rows_count, r))
			else:
				self.hide_table()

	def go_down(self, force=False, rows_count=1):
		"""
		Down in the table
		"""
		row_at_path = lambda p: p[0]

		table_visible = self.get_table_visible()
		# if no data is loaded (frex viewing catalog), load
		# if too little data is loaded, try load more
		if len(self.model) <= 1:
			self.populate(self.show_more)
		if len(self.model) >= 1:
			path, col = self.table.get_cursor()
			if path:
				r = row_at_path(path)
				if len(self.model) - rows_count <= r:
					self.populate(self.show_more)
				# go down only if table is visible
				if table_visible:
					step = min(len(self.model) - r - 1, rows_count)
					if step > 0:
						self._table_set_cursor_at_row(r + step)
			else:
				self._table_set_cursor_at_row(0)
			self._show_table()
		if force:
			self._show_table()

	def go_page_up(self):
		''' move list one page up '''
		self.go_up(self.page_step)

	def go_page_down(self):
		''' move list one page down '''
		self.go_down(rows_count=self.page_step)

	def go_first(self):
		''' Rewind to first item '''
		if self.get_table_visible():
			self._table_set_cursor_at_row(0)

	def _window_config(self, widget, event):
		"""
		When the window moves
		"""
		winpos = event.x, event.y
		# only hide on move, not resize
		# set old win position in _show_table
		if self.get_table_visible() and winpos != self._old_win_position:
			self.hide_table()
			gobject.timeout_add(300, self._show_table)

	def _window_hidden(self, window):
		"""
		Window changed hid
		"""
		self.hide_table()

	def _row_activated(self, treeview, path, col):
		obj = self.get_current()
		self.emit("activate", obj)

	def _cursor_changed(self, treeview):
		path, col = treeview.get_cursor()
		match = self.model.get_object(path)
		self._set_match(match)

	def _set_match(self, rankable=None):
		"""
		Set the currently selected (represented) object, either as
		@rankable or KupferObject @obj

		Emits cursor-changed
		"""
		self.match = (rankable.object if rankable else None)
		self.emit("cursor-changed", self.match)
		if self.match:
			match_text = (rankable and rankable.value)
			self.match_state = State.Match
			m = self.match
			pbuf = (m.get_thumbnail(self.icon_size*4//3, self.icon_size) or
				m.get_pixbuf(self.icon_size))
			self.match_view.set_match_state(match_text, pbuf,
					match=self.text, state=self.match_state)

	def set_match_plain(self, obj):
		"""Set match to object @obj, without search or matches"""
		self.text = None
		self._set_match(obj)
		self.model.add_first(obj)
		self._table_set_cursor_at_row(0)

	def relax_match(self):
		"""Remove match text highlight"""
		self.match_view.set_match_text(None)
		self.text = None

	def has_result(self):
		"""A search with explicit search term is active"""
		return self._has_search_result

	def is_showing_result(self):
		"""Showing search result:
		A search with explicit search term is active,
		and the result list is shown.
		"""
		return self._has_search_result and self.get_table_visible()

	def update_match(self, key, matchrankable, matches):
		"""
		@matchrankable: Rankable first match or None
		@matches: Iterable to rest of matches
		"""
		self._has_search_result = bool(key)
		self.model.clear()
		self.text = key
		if not matchrankable:
			self._set_match(None)
			return self.handle_no_matches(empty=not key)
		self._set_match(matchrankable)
		self.model.set_base(iter(matches))
		self._browsing_match = False
		if not self.model and self.get_table_visible():
			self.go_down()

	def reset(self):
		self._has_search_result = False
		self._initialized = True
		self.model.clear()
		self.setup_empty()

	def setup_empty(self):
		self.match_state = State.NoMatch
		self.match_view.set_match_state(u"No match", None, state=State.NoMatch)
		self.relax_match()

	def get_is_browsing(self):
		"""Return if self is browsing"""
		return self._browsing_match

	def populate(self, num):
		"""populate model with num items"""
		return self.model.populate(num)

	def handle_no_matches(self, empty=False):
		"""if @empty, there were no matches to find"""
		name, icon = self.get_nomatch_name_icon(empty=empty)
		self.match_state = State.NoMatch
		self.match_view.set_match_state(name, icon, state=State.NoMatch)

# Take care of gobject things to set up the Search class
gobject.type_register(Search)
gobject.signal_new("activate", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("cursor-changed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gtk.widget_class_install_style_property(Search,
		('list-opacity', gobject.TYPE_INT, 'Result list opacity',
		 'Opacity of the whole result list',
		 50, 100, 93,
		 gobject.PARAM_READABLE))

gtk.widget_class_install_style_property(Search,
		('list-length', gobject.TYPE_INT, 'Result list length',
		 'Maximum length of the result list',
		 50, 1024, 200,
		 gobject.PARAM_READABLE))

class LeafSearch (Search):
	"""
	Customize for leaves search
	"""
	def get_nomatch_name_icon(self, empty):
		get_pbuf = \
			lambda m: (m.get_thumbnail(self.icon_size*4/3, self.icon_size) or \
					m.get_pixbuf(self.icon_size))
		if empty and self.source:
			return (_("%s is empty") %
					escape_markup_str(unicode(self.source)),
					get_pbuf(self.source))
		elif self.source:
			return (_('No matches in %(src)s for "%(query)s"') % {
				"src": u"<i>%s</i>" % escape_markup_str(unicode(self.source)),
				"query": escape_markup_str(self.text),
				},
				get_pbuf(self.source))
		else:
			return _("No matches"), icons.get_icon_for_name("kupfer-object",
					self.icon_size)

	def setup_empty(self):
		icon = None
		title = _("Type to search")
		def get_pbuf(m):
			return (m.get_thumbnail(self.icon_size*4//3, self.icon_size) or
					m.get_pixbuf(self.icon_size))
		if self.source:
			icon = get_pbuf(self.source)
			title = (_("Type to search %s") %
					u"<i>%s</i>" % escape_markup_str(unicode(self.source)))

		self._set_match(None)
		self.match_state = State.Wait
		self.match_view.set_match_state(title, icon, state=State.Wait)

class ActionSearch (Search):
	"""
	Customization for Actions
	"""
	def get_nomatch_name_icon(self, empty=False):
		# don't look up icons too early
		if not self._initialized:
			return ("", None)
		return _("No action"), icons.get_icon_for_name("kupfer-execute",
				self.icon_size)
	def setup_empty(self):
		self.handle_no_matches()
		self.hide_table()

class Interface (gobject.GObject):
	"""
	Controller object that controls the input and
	the state (current active) search object/widget

	Signals:
	* cancelled: def callback(controller)
		escape was typed
	"""
	__gtype_name__ = "Interface"

	def __init__(self, controller, window):
		"""
		@controller: DataController
		@window: toplevel window
		"""
		gobject.GObject.__init__(self)

		self.search = LeafSearch()
		self.action = ActionSearch()
		self.third = LeafSearch()
		self.entry = gtk.Entry()
		self.label = gtk.Label()
		self.preedit = gtk.Entry()
		## make sure we lose the preedit focus ring
		self.preedit.set_name("kupfer-preedit")
		gtk.rc_parse_string("""
		style "kupferpreedit"
		{
			GtkEntry :: focus-line-width = 0
		}
		widget "*.%s" style "kupferpreedit"
		""" % (self.preedit.path(), ))

		self.current = None

		self._widget = None
		self._ui_transition_timer = scheduler.Timer()
		self._pane_three_is_visible = False
		self._is_text_mode = False
		self._latest_input_timer = scheduler.Timer()
		self._slow_input_interval = 2
		self._key_press_time = None
		self._key_press_interval = 0.3
		self._key_press_repeat_threshold = 0.02
		self._key_repeat_key = None
		self._key_repeat_active = False
		self._reset_to_toplevel = False
		self._reset_when_back = False
		self.entry.connect("realize", self._entry_realized)
		self.preedit.set_has_frame(False)
		self.preedit.set_inner_border(gtk.Border(0, 0, 0, 0))
		self.preedit.set_width_chars(0)
		self.preedit.set_alignment(1)

		from pango import ELLIPSIZE_MIDDLE
		self.label.set_width_chars(50)
		self.label.set_single_line_mode(True)
		self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
		self.label.set_name("kupfer-description")

		self.switch_to_source()
		self.entry.connect("changed", self._changed)
		self.preedit.connect("changed", self._preedit_changed)
		## preedit-changed is GTK+ 2.20
		## if not available, silently skip it
		try:
			self.preedit.connect("preedit-changed", self._preedit_im_changed)
		except TypeError:
			pass
		for widget in (self.entry, self.preedit):
			widget.connect("activate", self._activate, None)
			widget.connect("key-press-event", self._entry_key_press)
			widget.connect("key-release-event", self._entry_key_release)
			widget.connect("copy-clipboard", self._entry_copy_clipboard)
			widget.connect("cut-clipboard", self._entry_cut_clipboard)
			widget.connect("paste-clipboard", self._entry_paste_clipboard)

		# set up panewidget => self signals
		# as well as window => panewidgets
		for widget in (self.search, self.action, self.third):
			widget.connect("activate", self._activate)
			widget.connect("button-press-event", self._panewidget_button_press)
			widget.connect("cursor-changed", self._selection_changed)
			# window signals
			window.connect("configure-event", widget._window_config)
			window.connect("hide", widget._window_hidden)

		self.data_controller = controller
		self.data_controller.connect("search-result", self._search_result)
		self.data_controller.connect("source-changed", self._new_source)
		self.data_controller.connect("pane-reset", self._pane_reset)
		self.data_controller.connect("mode-changed", self._show_hide_third)
		self.data_controller.connect("object-stack-changed", self._object_stack_changed)
		self.widget_to_pane = {
			id(self.search) : data.SourcePane,
			id(self.action) : data.ActionPane,
			id(self.third) : data.ObjectPane,
			}
		self.pane_to_widget = {
			data.SourcePane : self.search,
			data.ActionPane : self.action,
			data.ObjectPane : self.third,
		}
		# Setup keyval mapping
		keys = (
			"Up", "Down", "Right", "Left",
			"Tab", "ISO_Left_Tab", "BackSpace", "Escape", "Delete",
			"space", 'Page_Up', 'Page_Down', 'Home', 'End',
			"Return",
			)
		self.key_book = dict((k, gtk.gdk.keyval_from_name(k)) for k in keys)
		if not text_direction_is_ltr():
			# for RTL languages, simply swap the meaning of Left and Right
			# (for keybindings!)
			D = self.key_book
			D["Left"], D["Right"] = D["Right"], D["Left"]

		self.keys_sensible = set(self.key_book.itervalues())
		self.search.reset()

	def get_widget(self):
		"""Return a Widget containing the whole Interface"""
		if self._widget:
			return self._widget
		box = gtk.HBox()
		box.pack_start(self.search, True, True, 3)
		box.pack_start(self.action, True, True, 3)
		box.pack_start(self.third, True, True, 3)
		vbox = gtk.VBox()
		vbox.pack_start(box, True, True, 0)

		label_align = gtk.Alignment(0.5, 1, 0, 0)
		label_align.set_property("top-padding", 3)
		label_align.add(self.label)
		vbox.pack_start(label_align, False, False, 0)
		vbox.pack_start(self.entry, False, False, 0)
		vbox.show_all()
		self.third.hide()
		self._widget = vbox
		return vbox

	def _entry_realized(self, widget):
		self.update_text_mode()

	def _entry_key_release(self, entry, event):
		# check for key repeat activation
		if self._key_repeat_key == event.keyval:
			if self._key_repeat_active:
				self.activate()
			self._key_repeat_key = None
			self._key_repeat_active = False
			self._update_active()

	def _entry_key_press(self, entry, event):
		"""
		Intercept arrow keys and manipulate table
		without losing focus from entry field
		"""

		direct_text_key = gtk.gdk.keyval_from_name("period")
		init_text_keys = map(gtk.gdk.keyval_from_name, ("slash", "equal"))
		init_text_keys.append(direct_text_key)
		keymap = gtk.gdk.keymap_get_default()
		# translate keys properly
		keyv, egroup, level, consumed = keymap.translate_keyboard_state(
					event.hardware_keycode, event.state, event.group)
		all_modifiers = gtk.accelerator_get_default_mod_mask()
		modifiers = all_modifiers & ~consumed
		# MOD1_MASK is alt/option
		mod1_mask = ((event.state & modifiers) == gtk.gdk.MOD1_MASK)
		shift_mask = ((event.state & all_modifiers) == gtk.gdk.SHIFT_MASK)

		text_mode = self.get_in_text_mode()
		has_input = bool(self.entry.get_text())

		curtime = time.time()
		self._reset_input_timer()

		setctl = settings.GetSettingsController()
		# process accelerators
		for action, accel in setctl.get_accelerators().iteritems():
			akeyv, amodf = gtk.accelerator_parse(accel)
			if not akeyv:
				continue
			if akeyv == keyv and (amodf == (event.state & modifiers)):
				action_method = getattr(self, action, None)
				if not action_method:
					pretty.print_error(__name__, "Action invalid '%s'" % action)
				else:
					action_method()
				return True

		key_book = self.key_book
		use_command_keys = setctl.get_use_command_keys()
		has_selection = (self.current.get_match_state() is State.Match)
		if not text_mode and use_command_keys:
			# translate extra commands to normal commands here
			# and remember skipped chars
			if keyv == key_book["space"]:
				if shift_mask:
					keyv = key_book["Up"]
				else:
					keyv = key_book["Down"]
			elif keyv == ord("/") and has_selection:
				keyv = key_book["Right"]
			elif keyv == ord(",") and has_selection:
				if self.comma_trick():
					return True
			elif keyv in init_text_keys:
				if self.try_enable_text_mode():
					# swallow if it is the direct key
					swallow = (keyv == direct_text_key)
					return swallow
		if text_mode and keyv in (key_book["Left"], key_book["Right"],
		                          key_book["Home"], key_book["End"]):
			# pass these through in text mode
			return False

		# check for repeated key activation
		if ((not text_mode) and self._key_repeat_key == keyv and
				keyv not in self.keys_sensible and
				curtime - self._key_press_time > self._key_press_repeat_threshold):
			if curtime - self._key_press_time > self._key_press_interval:
				self._key_repeat_active = True
				self._update_active()
			return True
		else:
			# cancel repeat key activation if a new key is pressed
			self._key_press_time = curtime
			self._key_repeat_key = keyv
			if self._key_repeat_active:
				self._key_repeat_active = False
				self._update_active()

		# exit here if it's not a special key
		if keyv not in self.keys_sensible:
			## if typing with shift key, switch to action pane
			if not text_mode and use_command_keys and shift_mask:
				uchar = gtk.gdk.keyval_to_unicode(keyv)
				if (uchar and unichr(uchar).isupper() and
				    self.current == self.search):
					self.current.hide_table()
					self.switch_current()
			return False
		self._reset_to_toplevel = False

		if keyv == key_book["Escape"]:
			self._escape_key_press()
			return True


		if keyv == key_book["Up"]:
			self.current.go_up()
		elif keyv == key_book["Page_Up"]:
			self.current.go_page_up()
		elif keyv == key_book["Down"]:
			## if typing with shift key, switch to action pane
			if shift_mask and self.current == self.search:
				self.current.hide_table()
				self.switch_current()
			if (not self.current.get_current() and
					self.current.get_match_state() is State.Wait):
				self._populate_search()
			self.current.go_down()
		elif keyv == key_book["Page_Down"]:
			if (not self.current.get_current() and
					self.current.get_match_state() is State.Wait):
				self._populate_search()
			self.current.go_page_down()
		elif keyv == key_book["Right"]:
			self._browse_down(alternate=mod1_mask)
		elif keyv == key_book["BackSpace"]:
			if not has_input:
				self._backspace_key_press()
			elif not text_mode:
				self.entry.delete_text(self.entry.get_text_length() - 1, -1)
			else:
				return False
		elif keyv == key_book["Left"]:
			self._back_key_press()
		elif keyv in (key_book["Tab"], key_book["ISO_Left_Tab"]):
			self.current.hide_table()
			self.switch_current(reverse=(keyv == key_book["ISO_Left_Tab"]))
		elif keyv == key_book['Home']:
			self.current.go_first()
		else:
			# cont. processing
			return False
		return True

	def _entry_copy_clipboard(self, entry):
		# Copy current selection to clipboard
		# delegate to text entry when in text mode

		if self.get_in_text_mode():
			return False
		selection = self.current.get_current()
		if selection is None:
			return False
		clip = gtk.Clipboard(selection=gtk.gdk.SELECTION_CLIPBOARD,
		                     display=entry.get_display())
		return interface.copy_to_clipboard(selection, clip)

	def _entry_cut_clipboard(self, entry):
		if not self._entry_copy_clipboard(entry):
			return False
		self.reset_current()
		self.reset()

	def _entry_paste_data_received(self, clipboard, targets, entry):
		uri_target = "text/uri-list"
		## check if we can insert files
		if uri_target in targets:
			# paste as files
			sdata = clipboard.wait_for_contents(uri_target)
			self.reset_current()
			self.reset()
			self.put_files(sdata.get_uris())
			## done
		else:
			# enable text mode and reemit to paste text
			self.try_enable_text_mode()
			if self.get_in_text_mode():
				entry.emit("paste-clipboard")

	def _entry_paste_clipboard(self, entry):
		if not self.get_in_text_mode():
			self.reset()
			## when not in text mode,
			## stop signal emission so we can handle it
			clipboard = gtk.Clipboard(selection=gtk.gdk.SELECTION_CLIPBOARD,
			                          display=entry.get_display())
			clipboard.request_targets(self._entry_paste_data_received, entry)
			entry.emit_stop_by_name("paste-clipboard")


	def reset_text(self):
		self.entry.set_text("")

	def reset(self):
		self.reset_text()
		self.current.hide_table()

	def reset_current(self, populate=False):
		"""
		Reset the source or action view

		Corresponds to backspace
		"""
		if self.current.get_match_state() is State.Wait:
			self.toggle_text_mode(False)
		if self.current is self.action or populate:
			self._populate_search()
		else:
			self.current.reset()

	def reset_all(self):
		"""Reset all panes and focus the first"""
		self.switch_to_source()
		while self._browse_up():
			pass
		self.toggle_text_mode(False)
		self.data_controller.object_stack_clear_all()
		self.reset_current()
		self.reset()

	def _populate_search(self):
		"""Do a blanket search/empty search to populate current pane"""
		pane = self._pane_for_widget(self.current)
		self.data_controller.search(pane, interactive=True)

	def soft_reset(self, pane=None):
		"""Reset @pane or current pane context/source
		softly (without visible update), and unset _reset_to_toplevel marker.
		"""
		pane = pane or self._pane_for_widget(self.current)
		newsrc = self.data_controller.soft_reset(pane)
		if newsrc:
			self.current.set_source(newsrc)
		self._reset_to_toplevel = False


	def _escape_key_press(self):
		"""Handle escape if first pane is reset, cancel (put away) self.  """
		if self.current.has_result():
			if self.current.is_showing_result():
				self.reset_current(populate=True)
			else:
				self.reset_current()
		else:
			if self.get_in_text_mode():
				self.toggle_text_mode(False)
			elif not self.current.get_table_visible():
				pane = self._pane_for_widget(self.current)
				self.data_controller.object_stack_clear(pane)
				self.emit("cancelled")
			self._reset_to_toplevel = True
			self.current.hide_table()
		self.reset_text()

	def _backspace_key_press(self):
		# backspace: delete from stack
		pane = self._pane_for_widget(self.current)
		if self.data_controller.get_object_stack(pane):
			self.data_controller.object_stack_pop(pane)
			self.reset_text()
			return
		self._back_key_press()

	def _back_key_press(self):
		# leftarrow (or backspace without object stack)
		# delete/go up through stource stack
		if self.current.is_showing_result():
			self.reset_current(populate=True)
		else:
			if self._browse_up():
				pass
			else:
				self.reset()
				self.reset_current()
				self._reset_to_toplevel = True
		self.reset_text()

	def _relax_search_terms(self):
		if self.get_in_text_mode():
			return
		self.reset_text()
		self.current.relax_match()

	def get_in_text_mode(self):
		return self._is_text_mode

	def get_can_enter_text_mode(self):
		"""We can enter text mode if the data backend allows,
		and the text entry is ready for input (empty)
		"""
		pane = self._pane_for_widget(self.current)
		val = self.data_controller.get_can_enter_text_mode(pane)
		entry_text = self.entry.get_text()
		return val and not entry_text

	def try_enable_text_mode(self):
		"""Perform a soft reset if possible and then try enabling text mode"""
		if self._reset_to_toplevel:
			self.soft_reset()
		if self.get_can_enter_text_mode():
			return self.toggle_text_mode(True)
		return False

	def toggle_text_mode(self, val):
		"""Toggle text mode on/off per @val,
		and return the subsequent on/off state.
		"""
		val = bool(val) and self.get_can_enter_text_mode()
		self._is_text_mode = val
		self.update_text_mode()
		self.reset()
		return val

	def toggle_text_mode_quick(self):
		"""Toggle text mode or not, if we can or not, without reset"""
		if self._is_text_mode:
			self._is_text_mode = False
		else:
			self._is_text_mode = True
		self.update_text_mode()

	def update_text_mode(self):
		"""update appearance to whether text mode enabled or not"""
		if self._is_text_mode:
			self.entry.show()
			self.entry.grab_focus()
			self.entry.set_position(-1)
			self.preedit.hide()
			self.preedit.set_width_chars(0)
		else:
			self.entry.hide()
		self._update_active()

	def switch_to_source(self):
		if self.current is not self.search:
			if self.current:
				self.current.hide_table()
			self.current = self.search
			self._update_active()
			if self.get_in_text_mode():
				self.toggle_text_mode_quick()

	def focus(self):
		"""called when the interface is focus (after being away)"""
		if self._reset_when_back:
			self._reset_when_back = False
			self.toggle_text_mode(False)
		# preserve text mode, but switch to source if we are not in it
		if not self.get_in_text_mode():
			self.switch_to_source()
		# Check that items are still valid when "coming back"
		self.data_controller.validate()

	def did_launch(self):
		"called to notify that 'activate' was successful"
		self._reset_when_back = True

	def put_away(self):
		"""Called when the interface is hidden"""
		self._relax_search_terms()
		self._reset_to_toplevel = True
		# no hide / show pane three on put away -> focus anymore

	def select_selected_file(self):
		# Add optional lookup data to narrow the search
		self.data_controller.find_object("qpfer:selectedfile#any.FileLeaf")

	def select_selected_text(self):
		self.data_controller.find_object("qpfer:selectedtext#any.TextLeaf")

	def select_quit(self):
		self.data_controller.find_object("qpfer:quit")

	def show_help(self):
		kupferui.show_help(self._make_gui_ctx())
		self.emit("launched-action")

	def show_preferences(self):
		kupferui.show_preferences(self._make_gui_ctx())
		self.emit("launched-action")

	def compose_action(self):
		self.data_controller.compose_selection()

	def mark_as_default(self):
		if self.action.get_match_state() != State.Match:
			return False
		self.data_controller.mark_as_default(data.ActionPane)
		return True

	def erase_affinity_for_first_pane(self):
		if self.search.get_match_state() != State.Match:
			return False
		self.data_controller.erase_object_affinity(data.SourcePane)
		return True

	def comma_trick(self):
		if self.current.get_match_state() != State.Match:
			return False
		cur = self.current.get_current()
		curpane = self._pane_for_widget(self.current)
		if self.data_controller.object_stack_push(curpane, cur):
			self._relax_search_terms()
			if self.get_in_text_mode():
				self.reset_text()
			return True

	def get_context_actions(self):
		"""
		Get a list of (name, function) currently
		active context actions
		"""
		def get_accel(key):
			""" Return name, method pair for @key"""
			if key not in accelerators.ACCELERATOR_NAMES:
				raise RuntimeError("Missing accelerator: %s" % key)
			return (accelerators.ACCELERATOR_NAMES[key], getattr(self, key))
		def trunc(ustr):
			"truncate long object names"
			return ustr[:25]
		has_match = self.current.get_match_state() == State.Match
		if has_match:
			yield get_accel('compose_action')
		yield get_accel('select_selected_text')
		if self.get_can_enter_text_mode():
			yield get_accel('toggle_text_mode_quick')
		if self.action.get_match_state() == State.Match:
			smatch = self.search.get_current()
			amatch = self.action.get_current()
			label = (_('Make "%(action)s" Default for "%(object)s"') % {
			         'action': trunc(unicode(amatch)),
			         'object': trunc(unicode(smatch)),
			         })
			w_label = textwrap.wrap(label, width=40, subsequent_indent="    ")
			yield (u"\n".join(w_label), self.mark_as_default)
		if has_match:
			if self.data_controller.get_object_has_affinity(data.SourcePane):
				match = self.search.get_current()
				# TRANS: Removing learned and/or configured bonus search score
				yield (_('Forget About "%s"') % trunc(unicode(match)),
				       self.erase_affinity_for_first_pane)
		if has_match:
			yield get_accel('reset_all')

	def _pane_reset(self, controller, pane, item):
		wid = self._widget_for_pane(pane)
		if not item:
			wid.reset()
		else:
			wid.set_match_plain(item)
			if wid is self.search:
				self.reset()
				self.toggle_text_mode(False)
				self.switch_to_source()

	def _new_source(self, sender, pane, source, at_root):
		"""Notification about a new data source,
		(represented object for the self.search object
		"""
		wid = self._widget_for_pane(pane)
		wid.set_source(source)
		wid.reset()
		if pane is data.SourcePane:
			self.switch_to_source()
			self.action.reset()
		if wid is self.current:
			self.toggle_text_mode(False)
			self._reset_to_toplevel = False
			if not at_root:
				self.reset_current(populate=True)
				wid.show_table()

	def _show_hide_third(self, ctr, mode, ignored):
		if mode is data.SourceActionObjectMode:
			# use a delay before showing the third pane,
			# but set internal variable to "shown" already now
			self._pane_three_is_visible = True
			self._ui_transition_timer.set_ms(200, self._show_third_pane, True)
		else:
			self._pane_three_is_visible = False
			self._show_third_pane(False)

	def _show_third_pane(self, show):
		self._ui_transition_timer.invalidate()
		self.third.set_property("visible", show)

	def _update_active(self):
		for panewidget in (self.action, self.search, self.third):
			if panewidget is not self.current:
				panewidget.set_state(gtk.STATE_NORMAL)
			panewidget.match_view.inject_preedit(None)
		if self._is_text_mode or self._key_repeat_active:
			self.current.set_state(gtk.STATE_ACTIVE)
		else:
			self.current.set_state(gtk.STATE_SELECTED)
			self.current.match_view.inject_preedit(self.preedit)
		self._description_changed()

	def switch_current(self, reverse=False):
		# Only allow switch if we have match
		order = [self.search, self.action]
		if self._pane_three_is_visible:
			order.append(self.third)
		curidx = order.index(self.current)
		newidx = curidx -1 if reverse else curidx +1
		newidx %= len(order)
		prev_pane = order[max(newidx -1, 0)]
		new_focus = order[newidx]
		if (prev_pane.get_match_state() is State.Match and
				new_focus is not self.current):
			self.current = new_focus
			# Use toggle_text_mode to reset
			self.toggle_text_mode(False)
			pane = self._pane_for_widget(new_focus)
			self._update_active()
			if self.data_controller.get_should_enter_text_mode(pane):
				self.toggle_text_mode_quick()

	def _browse_up(self):
		pane = self._pane_for_widget(self.current)
		return self.data_controller.browse_up(pane)

	def _browse_down(self, alternate=False):
		pane = self._pane_for_widget(self.current)
		self.data_controller.browse_down(pane, alternate=alternate)

	def _make_gui_ctx(self):
		timestamp = gtk.get_current_event_time()
		return uievents.gui_context_from_widget(timestamp, self._widget)

	def _activate(self, widget, current):
		self.data_controller.activate(ui_ctx=self._make_gui_ctx())

	def activate(self):
		"""Activate current selection (Run action)"""
		self._activate(None, None)

	def execute_file(self, filepath, display, timestamp):
		"""Execute a .kfcom file"""
		def _handle_error(exc_info):
			from kupfer import uiutils
			etype, exc, tb = exc_info
			if not uiutils.show_notification(unicode(exc), icon_name="kupfer"):
				raise
		ctxenv = uievents.gui_context_from_keyevent(timestamp, display)
		self.data_controller.execute_file(filepath, ctxenv, _handle_error)

	def _search_result(self, sender, pane, matchrankable, matches, context):
		# NOTE: "Always-matching" search.
		# If we receive an empty match, we ignore it, to retain the previous
		# results. The user is not served by being met by empty results.
		key = context
		if key and len(key) > 1 and matchrankable is None:
			# with typos or so, reset quicker
			self._latest_input_timer.set(self._slow_input_interval/2,
					self._relax_search_terms)
			return
		wid = self._widget_for_pane(pane)
		wid.update_match(key, matchrankable, matches)

	def _widget_for_pane(self, pane):
		return self.pane_to_widget[pane]
	def _pane_for_widget(self, widget):
		return self.widget_to_pane[id(widget)]

	def _object_stack_changed(self, controller, pane):
		"""
		Stack of objects (for comma trick) changed in @pane
		"""
		wid = self._widget_for_pane(pane)
		wid.set_object_stack(controller.get_object_stack(pane))

	def _panewidget_button_press(self, widget, event):
		" mouse clicked on a pane widget "
		# activate on double-click
		if event.type == gtk.gdk._2BUTTON_PRESS:
			self.activate()
			return True

	def _selection_changed(self, widget, match):
		pane = self._pane_for_widget(widget)
		self.data_controller.select(pane, match)
		if not widget is self.current:
			return
		self._description_changed()

	def _description_changed(self):
		match = self.current.get_current()
		desc = match and match.get_description() or ""
		markup = "<small>%s</small>" % (escape_markup_str(desc), )
		self.label.set_markup(markup)

	def put_text(self, text):
		"""
		Put @text into the interface to search, to use
		for "queries" from other sources
		"""
		self.try_enable_text_mode()
		self.entry.set_text(text)
		self.entry.set_position(-1)

	def put_files(self, fileuris):
		leaves = map(interface.get_fileleaf_for_path,
			filter(None, [gio.File(U).get_path() for U in fileuris]))
		if leaves:
			self.data_controller.insert_objects(data.SourcePane, leaves)

	def _reset_input_timer(self):
		# if input is slow/new, we reset
		self._latest_input_timer.set(self._slow_input_interval,
				self._relax_search_terms)

	def _preedit_im_changed(self, editable, preedit_string):
		"""
		This is called whenever the input method changes its own preedit box.
		We take this opportunity to expand it.
		"""
		if preedit_string:
			self.current.match_view.expand_preedit(self.preedit)
			self._reset_input_timer()

	def _preedit_changed(self, editable):
		"""
		The preedit has changed. As below, we need to use unicode.
		"""
		text = editable.get_text()
		text = text.decode("UTF-8")
		if text:
			self.entry.insert_text(text, -1)
			self.entry.set_position(-1)
			editable.delete_text(0, -1)
			# uncomment this to reset width after every commit.
			# self.current.match_view.shrink_preedit(self.preedit)
			self._reset_input_timer()

	def _changed(self, editable):
		"""
		The entry changed callback: Here we have to be sure to use
		**UNICODE** (unicode()) for the entered text
		"""
		# @text is UTF-8
		text = editable.get_text()
		text = text.decode("UTF-8")

		# draw character count as icon
		if self.get_in_text_mode() and text:
			w, h = editable.size_request()
			sz = h - 3
			c = editable.style.text[gtk.STATE_NORMAL]
			textc = (c.red/65535.0, c.green/65535.0, c.blue/65535.0)
			pb = get_glyph_pixbuf(str(len(text)), sz, color=textc)
			editable.set_icon_from_pixbuf(gtk.ENTRY_ICON_SECONDARY, pb)
		else:
			editable.set_icon_from_pixbuf(gtk.ENTRY_ICON_SECONDARY, None)

		# cancel search and return if empty
		if not text:
			self.data_controller.cancel_search()
			# See if it was a deleting key press
			curev = gtk.get_current_event()
			if (curev and curev.type == gtk.gdk.KEY_PRESS and
			    curev.keyval in (self.key_book["Delete"],
			        self.key_book["BackSpace"])):
				self._backspace_key_press()
			return

		# start search for updated query
		pane = self._pane_for_widget(self.current)
		if not self.get_in_text_mode() and self._reset_to_toplevel:
			self.soft_reset(pane)

		self.data_controller.search(pane, key=text, context=text,
				text_mode=self.get_in_text_mode())

gobject.type_register(Interface)
gobject.signal_new("cancelled", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
# Send only when the interface itself launched an action directly
gobject.signal_new("launched-action", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

class KupferWindow (gtk.Window):
	__gtype_name__ = "KupferWindow"
	def __init__(self, *args):
		super(KupferWindow, self).__init__(*args)
		self.connect("style-set", self.on_style_set)
		self.set_name("kupfer")
		self.connect("expose-event", self.on_expose_event)
		self.connect("size-allocate", self.on_size_allocate)
		self.connect("composited-changed", self.on_composited_changed)
		self.connect("realize", self.on_realize)
		self.set_app_paintable(True)

	def on_style_set(self, widget, old_style):
		widget.set_property('decorated',
				widget.style_get_property('decorated'))
		widget.set_property('border-width',
				widget.style_get_property('border-width'))

	def on_expose_event(self, widget, event):
		cr = widget.window.cairo_create()
		w,h = widget.allocation.width, widget.allocation.height

		region = gtk.gdk.region_rectangle(event.area)
		cr.region(region)
		cr.clip()

		def rgba_from_gdk(c, alpha):
			return (c.red/65535.0, c.green/65535.0, c.blue/65535.0, alpha)

		radius = widget.style_get_property('corner-radius')
		if widget.is_composited():
			opacity = 0.01*widget.style_get_property('opacity')
			#cr.set_operator(cairo.OPERATOR_CLEAR)
			cr.set_operator(cairo.OPERATOR_SOURCE)
			cr.set_source_rgba(0,0,0,0)
			cr.rectangle(0,0,w,h)
			cr.fill()
			#cr.rectangle(0,0,w,h)
			make_rounded_rect(cr, 0, 0, w, h, radius)
			cr.set_operator(cairo.OPERATOR_SOURCE)
			c = widget.style.bg[widget.get_state()]
			cr.set_source_rgba(*rgba_from_gdk(c, opacity))
			cr.fill()

		c = widget.style.dark[gtk.STATE_SELECTED]
		cr.set_operator(cairo.OPERATOR_ATOP)
		cr.set_source_rgba(*rgba_from_gdk(c, 0.7))

		make_rounded_rect(cr, 0, 0, w, h, radius)
		cr.set_line_width(1)
		cr.stroke()

	def on_composited_changed(self, widget):
		self.reshape(widget, widget.get_allocation())

	def on_realize(self, widget):
		self.reshape(widget, widget.get_allocation())

	def on_size_allocate(self, widget, allocation):
		if not hasattr(self, "_old_alloc"):
			self._old_alloc = (0,0)
		w,h = allocation.width, allocation.height

		if self._old_alloc == (w,h):
			return
		self._old_alloc = (w,h)
		self.reshape(widget, allocation)

	def reshape(self, widget, allocation):
		## if not composited, use rounded window shape
		w,h = allocation.width, allocation.height
		radius = widget.style_get_property('corner-radius')
		if not widget.is_composited() and radius:
			bitmap = gtk.gdk.Pixmap(None, w, h, 1)
			cr = bitmap.cairo_create()

			cr.set_source_rgb(0.0, 0.0, 0.0)
			cr.set_operator(cairo.OPERATOR_CLEAR)
			cr.paint()

			# radius of rounded corner
			cr.set_source_rgb(1.0, 1.0, 1.0)
			cr.set_operator(cairo.OPERATOR_SOURCE)
			make_rounded_rect(cr, 0, 0, w, h, radius)
			cr.fill()
			widget.shape_combine_mask(bitmap, 0, 0)
		else:
			if widget.window:
				widget.window.shape_combine_mask(None, 0, 0)
		if widget.window:
			widget.window.invalidate_rect(gtk.gdk.Rectangle(0, 0, w, h), False)


gobject.type_register(KupferWindow)
gtk.widget_class_install_style_property(KupferWindow,
		('corner-radius', gobject.TYPE_INT, 'Corner radius',
		 'Radius of bezel around window',
		 0, 50, 15,
		 gobject.PARAM_READABLE))
gtk.widget_class_install_style_property(KupferWindow,
		('opacity', gobject.TYPE_INT, 'Frame opacity',
		 'Opacity of window background',
		 50, 100, 85,
		 gobject.PARAM_READABLE))
gtk.widget_class_install_style_property(KupferWindow,
		('decorated', gobject.TYPE_BOOLEAN, 'Decorated',
		 'Whether to use window decorations',
		 False,
		 gobject.PARAM_READABLE))

gtk.widget_class_install_style_property(KupferWindow,
		('border-width', gobject.TYPE_INT, 'Border width',
		 'Width of border around window content',
		 0, 100, 8,
		 gobject.PARAM_READABLE))

class WindowController (pretty.OutputMixin):
	"""
	This is the fundamental Window (and App) Controller
	"""
	def __init__(self):
		self.window = None
		self.current_screen_handler = 0
		self.current_screen = None
		self.interface = None
		self._statusicon = None
		self._window_hide_timer = scheduler.Timer()

	def initialize(self, data_controller):
		self.window = KupferWindow(gtk.WINDOW_TOPLEVEL)
		self.window.add_events(gtk.gdk.BUTTON_PRESS_MASK)

		#data_controller = data.DataController()
		data_controller.connect("launched-action", self.launch_callback)
		data_controller.connect("command-result", self.result_callback)

		self.interface = Interface(data_controller, self.window)
		self.interface.connect("launched-action", self.launch_callback)
		self.interface.connect("cancelled", self._cancelled)
		self._setup_window()

	def show_statusicon(self):
		if not self._statusicon:
			self._statusicon = self._setup_status_icon()
		try:
			self._statusicon.set_visible(True)
		except AttributeError:
			pass

	def hide_statusicon(self):
		if self._statusicon:
			try:
				self._statusicon.set_visible(False)
			except AttributeError:
				self._statusicon = None

	def _showstatusicon_changed(self, setctl, section, key, value):
		"callback from SettingsController"
		if value:
			self.show_statusicon()
		else:
			self.hide_statusicon()

	def _setup_menu(self, context_menu=False):
		menu = gtk.Menu()
		menu.set_name("kupfer-menu")

		def submenu_callback(menuitem, callback):
			callback()
			return True

		def add_menu_item(icon, callback, label=None, with_ctx=True):
			def mitem_handler(menuitem, callback):
				if with_ctx:
					time = gtk.get_current_event_time()
					ui_ctx = uievents.gui_context_from_widget(time, menuitem)
					callback(ui_ctx)
				else:
					callback()
				if context_menu:
					self.put_away()
				return True

			mitem = None
			if label and not icon:
				mitem = gtk.MenuItem(label=label)
			else:
				mitem = gtk.ImageMenuItem(icon)
			mitem.connect("activate", mitem_handler, callback)
			menu.append(mitem)

		if context_menu:
			add_menu_item(gtk.STOCK_CLOSE, self.put_away, with_ctx=False)
		else:
			add_menu_item(None, self.activate, _("Show Main Interface"))
		menu.append(gtk.SeparatorMenuItem())
		if context_menu:
			for name, func in self.interface.get_context_actions():
				mitem = gtk.MenuItem(label=name)
				mitem.connect("activate", submenu_callback, func)
				menu.append(mitem)
			menu.append(gtk.SeparatorMenuItem())

		add_menu_item(gtk.STOCK_PREFERENCES, kupferui.show_preferences)
		add_menu_item(gtk.STOCK_HELP, kupferui.show_help)
		add_menu_item(gtk.STOCK_ABOUT, kupferui.show_about_dialog)
		menu.append(gtk.SeparatorMenuItem())
		add_menu_item(gtk.STOCK_QUIT, self.quit, with_ctx=False)
		menu.show_all()

		return menu

	def _setup_status_icon(self):
		menu = self._setup_menu()
		try:
			import appindicator
		except ImportError:
			appindicator = None
		else:
			## make sure dbus is available, else appindicator crashes
			import dbus
			try:
				dbus.Bus()
			except dbus.DBusException:
				appindicator = None
		if appindicator:
			return self._setup_appindicator(menu)
		else:
			return self._setup_gtk_status_icon(menu)

	def _setup_gtk_status_icon(self, menu):
		status = gtk.status_icon_new_from_icon_name(version.ICON_NAME)
		status.set_tooltip(version.PROGRAM_NAME)

		status.connect("popup-menu", self._popup_menu, menu)
		status.connect("activate", self.show_hide)
		return status

	def _setup_appindicator(self, menu):
		import appindicator
		indicator = appindicator.Indicator(version.PROGRAM_NAME,
			version.ICON_NAME,
			appindicator.CATEGORY_APPLICATION_STATUS)
		indicator.set_status(appindicator.STATUS_ACTIVE)

		indicator.set_menu(menu)
		return indicator

	def _setup_window(self):
		"""
		Returns window
		"""

		self.window.connect("delete-event", self._close_window)
		self.window.connect("focus-out-event", self._lost_focus)
		self.window.connect("button-press-event", self._window_frame_clicked)
		widget = self.interface.get_widget()
		widget.show()

		# Build the window frame with its top bar
		topbar = gtk.HBox()
		vbox = gtk.VBox()
		vbox.pack_start(topbar, False, False)
		vbox.pack_start(widget, True, True)
		vbox.show()
		self.window.add(vbox)
		title = gtk.Label(u"")
		button = gtk.Label(u"")
		l_programname = version.PROGRAM_NAME.lower()
		# The text on the general+context menu button
		btext = u"<b>%s \N{GEAR}</b>" % (l_programname, )
		button.set_markup(btext)
		button_box = gtk.EventBox()
		button_box.set_visible_window(False)
		button_adj = gtk.Alignment(0.5, 0.5, 0, 0)
		button_adj.set_padding(0, 2, 0, 3)
		button_adj.add(button)
		button_box.add(button_adj)
		button_box.connect("button-press-event", self._context_clicked)
		button_box.connect("enter-notify-event", self._button_enter,
						   button, btext)
		button_box.connect("leave-notify-event", self._button_leave,
						   button, btext)
		button.set_name("kupfer-menu-button")
		title_align = gtk.Alignment(0, 0.5, 0, 0)
		title_align.add(title)
		topbar.pack_start(title_align, True, True)
		topbar.pack_start(button_box, False, False)
		topbar.show_all()

		self.window.set_title(version.PROGRAM_NAME)
		self.window.set_icon_name(version.ICON_NAME)
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
		self.window.set_property("skip-taskbar-hint", True)
		self.window.set_keep_above(True)

		if not text_direction_is_ltr():
			self.window.set_gravity(gtk.gdk.GRAVITY_NORTH_EAST)
		# Setting not resizable changes from utility window
		# on metacity
		self.window.set_resizable(False)

	def _window_frame_clicked(self, widget, event):
		"Start drag when the window is clicked"
		widget.begin_move_drag(event.button,
				int(event.x_root), int(event.y_root), event.time)

	def _context_clicked(self, widget, event):
		"The context menu label was clicked"
		menu = self._setup_menu(True)
		menu.set_screen(self.window.get_screen())
		menu.popup(None, None, None, event.button, event.time)
		return True

	def _button_enter(self, widget, event, button, udata):
		"Pointer enters context menu button"
		button.set_markup("<u>" + udata + "</u>")

	def _button_leave(self, widget, event, button, udata):
		"Pointer leaves context menu button"
		button.set_markup(udata)

	def _popup_menu(self, status_icon, button, activate_time, menu):
		"""
		When the StatusIcon is right-clicked
		"""
		menu.popup(None, None, gtk.status_icon_position_menu, button, activate_time, status_icon)

	def launch_callback(self, sender):
		# Separate window hide from the action being
		# done. This is to solve a window focus bug when
		# we switch windows using an action
		self.interface.did_launch()
		self._window_hide_timer.set_ms(100, self.put_away)

	def result_callback(self, sender, result_type, ui_ctx):
		if ui_ctx:
			self.on_present(sender, ui_ctx.get_display(), ui_ctx.get_timestamp())
		else:
			self.on_present(sender, "", gtk.get_current_event_time())

	def _lost_focus(self, window, event):
		# Close at unfocus.
		# Since focus-out-event is triggered even
		# when we click inside the window, we'll
		# do some additional math to make sure that
		# that window won't close if the mouse pointer
		# is over it.
		x, y, mods = window.get_screen().get_root_window().get_pointer()
		w_x, w_y = window.get_position()
		w_w, w_h = window.get_size()
		if (x not in xrange(w_x, w_x + w_w) or
			y not in xrange(w_y, w_y + w_h)):
			self._window_hide_timer.set_ms(50, self.put_away)

	def _monitors_changed(self, *ignored):
		self._center_window()

	def is_current_display(self, displayname):
		def norm_name(name):
			"Make :0.0 out of :0"
			if name[-2] == ":":
				return name + ".0"
			return name
		if not self.window.has_screen():
			return False
		cur_disp = self.window.get_screen().get_display().get_name()
		return norm_name(cur_disp) == norm_name(displayname)

	def _window_put_on_screen(self, screen):
		if self.current_screen_handler:
			scr = self.window.get_screen()
			scr.disconnect(self.current_screen_handler)
		rgba = screen.get_rgba_colormap()
		if rgba:
			self.window.unrealize()
			self.window.set_screen(screen)
			self.window.set_colormap(rgba)
			self.window.realize()
		else:
			self.window.set_screen(screen)
		self.current_screen_handler = \
			screen.connect("monitors-changed", self._monitors_changed)
		self.current_screen = screen

	def _center_window(self, displayname=None):
		"""Center Window on the monitor the pointer is currently on"""
		def norm_name(name):
			"Make :0.0 out of :0"
			if name[-2] == ":":
				return name + ".0"
			return name
		if not displayname and self.window.has_screen():
			display = self.window.get_display()
		else:
			display = uievents.GUIEnvironmentContext.ensure_display_open(displayname)
		screen, x, y, modifiers = display.get_pointer()
		self._window_put_on_screen(screen)
		monitor_nr = screen.get_monitor_at_point(x, y)
		geo = screen.get_monitor_geometry(monitor_nr)
		wid, hei = self.window.get_size()
		midx = geo.x + geo.width / 2 - wid / 2
		midy = geo.y + geo.height / 2 - hei / 2
		self.window.move(midx, midy)
		uievents.GUIEnvironmentContext._try_close_unused_displays(screen)

	def _should_recenter_window(self):
		"""Return True if the mouse pointer and the window
		are on different monitors.
		"""
		# Check if the GtkWindow was realized yet
		if not self.window.window:
			return True
		display = self.window.get_screen().get_display()
		screen, x, y, modifiers = display.get_pointer()
		return (screen.get_monitor_at_point(x,y) !=
		        screen.get_monitor_at_window(self.window.window))

	def activate(self, sender=None):
		dispname = self.window.get_screen().make_display_name()
		self.on_present(sender, dispname, gtk.get_current_event_time())

	def on_present(self, sender, display, timestamp):
		"""Present on @display, where None means default display"""
		self._window_hide_timer.invalidate()
		if not display:
			display = gtk.gdk.display_get_default().get_name()
		if (self._should_recenter_window() or
		    not self.is_current_display(display)):
			self._center_window(display)
		self.window.stick()
		self.window.present_with_time(timestamp)
		self.window.window.focus(timestamp=timestamp)
		self.interface.focus()

	def put_away(self):
		self.interface.put_away()
		self.window.hide()

	def _cancelled(self, widget):
		self.put_away()

	def on_show_hide(self, sender, display, timestamp):
		"""
		Toggle activate/put-away
		"""
		if self.window.get_property("visible"):
			self.put_away()
		else:
			self.on_present(sender, display, timestamp)

	def show_hide(self, sender):
		"GtkStatusIcon callback"
		self.on_show_hide(sender, "", gtk.get_current_event_time())

	def _key_binding(self, keyobj, keybinding_number, display, timestamp):
		"""Keybinding activation callback"""
		if keybinding_number == keybindings.KEYBINDING_DEFAULT:
			self.on_show_hide(keyobj, display, timestamp)
		elif keybinding_number == keybindings.KEYBINDING_MAGIC:
			self.on_present(keyobj, display, timestamp)
			self.interface.select_selected_text()
			self.interface.select_selected_file()

	def on_put_text(self, sender, text, display, timestamp):
		"""We got a search text from dbus"""
		self.on_present(sender, display, timestamp)
		self.interface.put_text(text)

	def on_put_files(self, sender, fileuris, display, timestamp):
		self.on_present(sender, display, timestamp)
		self.interface.put_files(fileuris)

	def on_execute_file(self, sender, filepath, display, timestamp):
		self.interface.execute_file(filepath, display, timestamp)

	def _close_window(self, window, event):
		self.put_away()
		return True

	def _destroy(self, widget, data=None):
		self.quit()

	def _sigterm(self, signal, frame):
		self.output_info("Caught signal", signal, "exiting..")
		self.quit()

	def _on_early_interrupt(self, signal, frame):
		sys.exit(1)

	def save_data(self):
		"""Save state before quit"""
		sch = scheduler.GetScheduler()
		sch.finish()

	def quit(self, sender=None):
		gtk.main_quit()

	def quit_now(self):
		"""Quit immediately (state save should already be done)"""
		raise SystemExit

	def _session_save(self, *args):
		"""Old-style session save callback.
		ret True on successful
		"""
		# No quit, only save
		self.output_info("Saving for logout...")
		self.save_data()
		return True

	def _session_die(self, *args):
		"""Session callback on session end
		quit now, without saving, since we already do that on
		Session save!
		"""
		self.quit_now()

	def lazy_setup(self):
		"""Do all setup that can be done after showing main interface.
		Connect to desktop services (keybinding callback, session logout
		callbacks etc).
		"""
		from kupfer.ui import session

		self.output_debug("in lazy_setup")

		setctl = settings.GetSettingsController()
		if setctl.get_show_status_icon():
			self.show_statusicon()
		setctl.connect("value-changed::kupfer.showstatusicon",
		               self._showstatusicon_changed)
		keystr = setctl.get_keybinding()
		magickeystr = setctl.get_magic_keybinding()

		if keystr:
			succ = keybindings.bind_key(keystr)
			self.output_info("Trying to register %s to spawn kupfer.. %s"
					% (keystr, "success" if succ else "failed"))


		if magickeystr:
			succ = keybindings.bind_key(magickeystr,
					keybindings.KEYBINDING_MAGIC)
			self.output_debug("Trying to register %s to spawn kupfer.. %s"
					% (magickeystr, "success" if succ else "failed"))
		keyobj = keybindings.GetKeyboundObject()
		keyobj.connect("keybinding", self._key_binding)

		signal.signal(signal.SIGINT, self._sigterm)
		signal.signal(signal.SIGTERM, self._sigterm)
		signal.signal(signal.SIGHUP, self._sigterm)

		client = session.SessionClient()
		client.connect("save-yourself", self._session_save)
		client.connect("die", self._session_die)

		self.output_debug("finished lazy_setup")

	def main(self, quiet=False):
		"""Start WindowController, present its window (if not @quiet)"""
		signal.signal(signal.SIGINT, self._on_early_interrupt)

		try:
			kserv = listen.Service()
		except listen.AlreadyRunningError:
			self.output_info("An instance is already running, exiting...")
			self.quit_now()
		except listen.NoConnectionError:
			kserv = None
		else:
			keyobj = keybindings.GetKeyboundObject()
			keyobj.connect("bound-key-changed",
			               lambda x,y,z: kserv.BoundKeyChanged(y,z))
			kserv.connect("relay-keys", keyobj.relayed_keys)

		# Load data
		data_controller = data.DataController()
		sch = scheduler.GetScheduler()
		sch.load()
		# Now create UI and display
		self.initialize(data_controller)
		sch.display()

		if kserv:
			kserv.connect("present", self.on_present)
			kserv.connect("show-hide", self.on_show_hide)
			kserv.connect("put-text", self.on_put_text)
			kserv.connect("put-files", self.on_put_files)
			kserv.connect("execute-file", self.on_execute_file)
			kserv.connect("quit", self.quit)

		if not quiet:
			self.activate()
		gobject.idle_add(self.lazy_setup)

		def do_main_iterations(max_events=0):
			# use sentinel form of iter
			for idx, pending in enumerate(iter(gtk.events_pending, False)):
				if max_events and idx > max_events:
					break
				gtk.main_iteration()

		try:
			gtk.main()
			# put away window *before exiting further*
			self.put_away()
			do_main_iterations(10)
		finally:
			self.save_data()

		# tear down but keep hanging
		if kserv:
			kserv.unregister()
		keybindings.bind_key(None, keybindings.KEYBINDING_DEFAULT)
		keybindings.bind_key(None, keybindings.KEYBINDING_MAGIC)

		do_main_iterations(100)
		# if we are still waiting, print a message
		if gtk.events_pending():
			self.output_info("Waiting for tasks to finish...")
			do_main_iterations()
