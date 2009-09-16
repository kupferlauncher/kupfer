#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import itertools
import os
import time

import pygtk
pygtk.require('2.0')

import gtk
import gio
import gobject

from kupfer import data, icons, scheduler, relevance
from kupfer import keybindings
from kupfer import pretty


def escape_markup_str(mstr):
	"""
	Use a simeple homegrown replace table to replace &, <, > with
	entities in @mstr
	"""
	escape_table = {u"&": u"&amp;", u"<": u"&lt;", u">": u"&gt;" }
	escape = lambda c: escape_table.get(c, c)
	return u"".join(escape(c) for c in mstr)

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
		return 24
	def get_icon(self, leaf):
		sz = self.get_icon_size()
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
		content_mark = (u"\u2023").decode("UTF-8")
		info = ""
		if hasattr(leaf, "has_content") and leaf.has_content():
			info = content_mark
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

	def __init__(self, icon_size):
		gobject.GObject.__init__(self)
		# object attributes
		self.label_char_width = 25
		self.match_state = State.Wait
		self.icon_size = icon_size
		# finally build widget
		self.build_widget()
		self.cur_icon = None
		self.cur_text = None
		self.cur_match = None

		# Get the current selection color
		ent = gtk.Entry()
		selectedc = ent.style.bg[gtk.STATE_SELECTED]
		activec = gtk.gdk.color_parse("light blue")
		self.event_box.modify_bg(gtk.STATE_SELECTED, selectedc)
		self.event_box.modify_bg(gtk.STATE_ACTIVE, activec)

	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""
		from pango import ELLIPSIZE_MIDDLE
		self.label = gtk.Label("<match>")
		self.label.set_justify(gtk.JUSTIFY_CENTER)
		self.label.set_width_chars(self.label_char_width)
		self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
		self.icon_view = gtk.Image()

		# infobox: icon and match name
		infobox = gtk.HBox()
		infobox.pack_start(self.icon_view, True, True, 0)
		box = gtk.VBox()
		box.pack_start(infobox, True, False, 0)
		box.pack_start(self.label, False, True, 0)
		self.event_box = gtk.EventBox()
		self.event_box.add(box)
		self.add(self.event_box)
		self.event_box.show_all()
		self.__child = self.event_box

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)
		
	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		# update icon
		icon = self.cur_icon
		if icon:
			if self.match_state is State.NoMatch:
				icon = self._dim_icon(icon)
			self.icon_view.set_from_pixbuf(icon)
		else:
			self.icon_view.set_from_icon_name("gtk-file", self.icon_size)
			self.icon_view.set_pixel_size(self.icon_size)

		if not self.cur_text:
			self.label.set_text("<no text>")
			return
		
		if not self.cur_match or self.match_state is not State.Match:
			self.label.set_text(self.cur_text)
			return

		# update the text label
		text = self.cur_text
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
	
	def set_state(self, state):
		"""
		Widget state (Active/normal/prelight etc)
		"""
		super(MatchView, self).set_state(state)
		#self.label.set_state(gtk.STATE_NORMAL)
		self.event_box.queue_draw()

gobject.type_register(MatchView)

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
		self.text = ""
		# internal constants
		self.show_initial = 10
		self.show_more = 10
		self.source = None
		self.icon_size = 96
		self._old_win_position=None
		self._has_search_result = False
		# finally build widget
		self.build_widget()
		self.setup_empty()
	
	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""
		self.match_view = MatchView(self.icon_size)

		self.table = gtk.TreeView(self.model.get_store())
		self.table.set_headers_visible(False)
		self.table.set_property("enable-search", False)

		for col in self.model.columns:
			self.table.append_column(col)

		self.table.connect("row-activated", self._row_activated)
		self.table.connect("key-press-event", self._table_key_press)
		self.table.connect("cursor-changed", self._cursor_changed)

		self.scroller = gtk.ScrolledWindow()
		self.scroller.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		self.scroller.add(self.table)
		vscroll = self.scroller.get_vscrollbar()
		vscroll.connect("change-value", self._table_scroll_changed)

		self.list_window = gtk.Window(gtk.WINDOW_POPUP)

		box = gtk.VBox()
		box.pack_start(self.match_view, True, True, 0)
		self.add(box)
		box.show_all()
		self.__child = box

		self.list_window.add(self.scroller)
		self.scroller.show_all()
	
	def _table_key_press(self, treeview, event):
		"""
		Catch keypresses in the treeview and divert them
		"""
		self.emit("table-event", treeview, event)
		return True
	
	def get_current(self):
		"""
		return current selection
		"""
		return self.match

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
		# self.window is a GdkWindow
		win_width, win_height = self.window.get_size()
		pos_x, pos_y = self.window.get_position()
		lowerc = pos_y + win_height
		table_w, table_len = self.table.size_request()
		subwin_height = min(table_len, 200)
		subwin_width = self.list_window.size_request()[0]
		self.list_window.move(pos_x, lowerc)
		self.list_window.resize(subwin_width, subwin_height)

		win = self.get_toplevel()
		self.list_window.set_transient_for(win)
		self.list_window.set_property("focus-on-map", False)
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

	def go_up(self):
		"""
		Upwards in the table
		"""
		row_at_path = lambda p: p[0]

		# go up, simply. close table if we go up from row 0
		path, col = self.table.get_cursor()
		if path:
			r = row_at_path(path)
			if r >= 1:
				self._table_set_cursor_at_row(r-1)
			else:
				self.hide_table()
	
	def go_down(self, force=False):
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
				if r == -1 + len(self.model):
					self.populate(self.show_more)
				# go down only if table is visible
				if r < -1 + len(self.model) and table_visible:
					self._table_set_cursor_at_row(r+1)
			else:
				self._table_set_cursor_at_row(0)
			self._show_table()
		if force:
			self._show_table()
	
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
			pbuf = (m.get_thumbnail(self.icon_size*4/3, self.icon_size) or
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
	
	def set_active(self, act):
		self.active = act
		state = (gtk.STATE_NORMAL, gtk.STATE_SELECTED)[act]
		self.match_view.set_state(state)

# Take care of gobject things to set up the Search class
gobject.type_register(Search)
gobject.signal_new("activate", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("cursor-changed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("table-event", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_OBJECT, gobject.TYPE_PYOBJECT))

class LeafSearch (Search):
	"""
	Customize for leaves search	
	"""
	def __init__(self, **kwargs):
		from objects import DummyLeaf
		self.dummy = DummyLeaf()
		super(LeafSearch, self).__init__(**kwargs)
	def get_nomatch_name_icon(self, empty):
		get_pbuf = \
			lambda m: (m.get_thumbnail(self.icon_size*4/3, self.icon_size) or \
					m.get_pixbuf(self.icon_size))
		if empty and self.source:
			return _("%s is empty") % self.source, get_pbuf(self.source)
		elif self.source:
			return (_('No matches in %s for "%s"') % (self.source, self.text),
					get_pbuf(self.source))
		else:
			return unicode(self.dummy), self.dummy.get_pixbuf(self.icon_size)
	def setup_empty(self):
		icon = None
		title = _("Searching...")
		get_pbuf = \
			lambda m: (m.get_thumbnail(self.icon_size*4/3, self.icon_size) or \
					m.get_pixbuf(self.icon_size))
		if self.source:
			icon = get_pbuf(self.source)
			title = _("Searching %(source)s...") % {"source":self.source}

		self._set_match(None)
		self.match_state = State.Wait
		self.match_view.set_match_state(unicode(title), icon, state=State.Wait)

class ActionSearch (Search):
	"""
	Customization for Actions
	"""
	def __init__(self, **kwargs):
		from objects import DummyAction
		self.dummy = DummyAction()
		super(ActionSearch, self).__init__(**kwargs)
	def get_nomatch_name_icon(self, empty=False):
		return unicode(self.dummy), self.dummy.get_pixbuf(self.icon_size)
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

		self.current = None

		self._widget = None
		self._current_ui_transition = -1
		self._pane_three_is_visible = False
		self._is_text_mode = False
		self._latest_input_timer = scheduler.Timer()
		self._slow_input_interval = 2
		self._key_press_time = None
		self._key_press_interval = 0.8
		self._key_pressed = None
		self._theme_colors = {}
		self._reset_to_toplevel = False
		self.entry.set_size_request(0, 0)
		window.connect("map-event", self._map_window)

		from pango import ELLIPSIZE_END
		self.label.set_width_chars(50)
		self.label.set_ellipsize(ELLIPSIZE_END)

		self.switch_to_source()
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate, None)
		self.entry.connect("key-press-event", self._entry_key_press)
		self.entry.connect("key-release-event", self._entry_key_release)
		self.entry.connect("paste-clipboard", self._entry_paste_clipboard)

		# set up panewidget => self signals
		# as well as window => panewidgets
		for widget in (self.search, self.action, self.third):
			widget.connect("table-event", self._table_event)
			widget.connect("activate", self._activate)
			widget.connect("cursor-changed", self._selection_changed)
			widget.connect("button-press-event", self._pane_button_press)
			# window signals
			window.connect("configure-event", widget._window_config)
			window.connect("hide", widget._window_hidden)

		self.data_controller = controller
		self.data_controller.connect("search-result", self._search_result)
		self.data_controller.connect("source-changed", self._new_source)
		self.data_controller.connect("pane-reset", self._pane_reset)
		self.data_controller.connect("mode-changed", self._show_hide_third)
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
			"space",
			)
		self.key_book = dict((k, gtk.gdk.keyval_from_name(k)) for k in keys)
		self.keys_sensible = set(self.key_book.itervalues())
		self.search.reset()

	def get_widget(self):
		"""Return a Widget containing the whole Interface"""
		if self._widget:
			return self._widget
		box = gtk.HBox()
		box.pack_start(self.search, True, True, 0)
		box.pack_start(self.action, True, True, 0)
		box.pack_start(self.third, True, True, 0)
		vbox = gtk.VBox()
		vbox.pack_start(box, True, True, 0)
		vbox.pack_start(self.label, True, True, 0)
		vbox.pack_start(self.entry, True, True, 0)
		vbox.show_all()
		self.label.hide()
		self.third.hide()
		self._widget = vbox
		return vbox

	def _map_window(self, widget, event):
		"""When Interface's widget is mapped and shown on the screen"""
		# Now we can read the style from the real theme
		if not self._theme_colors:
			self._theme_colors["bg"] = self.entry.style.bg[gtk.STATE_NORMAL]
			self._theme_colors["text"] = self.entry.style.text[gtk.STATE_NORMAL]
		self.update_text_mode()

	def _pane_button_press(self, widget, event):
		window = widget.get_toplevel()
		window.begin_move_drag(event.button,
				int(event.x_root), int(event.y_root), event.time)

	def _entry_key_release(self, entry, event):
		self._key_pressed = None

	def _entry_key_press(self, entry, event):
		"""
		Intercept arrow keys and manipulate table
		without losing focus from entry field
		"""
		keyv = event.keyval
		key_book = self.key_book

		# FIXME: These should be configurable
		accels = {
			"<Control>period" : "toggle_text_mode_quick",
			"<Control>s" : "switch_to_source",
			"<Control>r" : "reset_all",
			"<Control>g" : "select_selected_file",
			"<Control>t" : "select_selected_text",
		}
		direct_text_key = gtk.gdk.keyval_from_name("period")
		init_text_keys = map(gtk.gdk.keyval_from_name, ("slash", "equal"))
		init_text_keys.append(direct_text_key)
		# test for alt modifier (MOD1_MASK is alt/option)
		modifiers = gtk.accelerator_get_default_mod_mask()
		mod1_mask = ((event.state & modifiers) == gtk.gdk.MOD1_MASK)
		shift_mask = ((event.state & modifiers) == gtk.gdk.SHIFT_MASK)

		text_mode = self.get_in_text_mode()
		has_input = bool(self.entry.get_text())

		curtime = time.time()
		# if input is slow/new, we reset
		self._latest_input_timer.set(self._slow_input_interval,
				self._relax_search_terms)

		# process accelerators
		for accel in accels:
			akeyv, amodf = gtk.accelerator_parse(accel)
			if not akeyv:
				continue
			if akeyv == keyv and (amodf == (event.state & modifiers)):
				action = accels[accel]
				action_method = getattr(self, action, None)
				if not action_method:
					pretty.print_error(__name__, "Action invalid '%s'" % action)
				else:
					action_method()
				return True

		has_selection = (self.current.get_match_state() is State.Match)
		if not text_mode:
			# translate extra commands to normal commands here
			# and remember skipped chars
			if keyv == key_book["space"]:
				if shift_mask:
					keyv = key_book["Up"]
				else:
					keyv = key_book["Down"]
			elif keyv == ord("/") and has_selection:
				keyv = key_book["Right"]
			elif keyv in init_text_keys:
				if self.try_enable_text_mode():
					# swallow if it is the direct key
					swallow = (keyv == direct_text_key)
					return swallow
		elif keyv in (key_book["Left"], key_book["Right"]):
			# pass these through in text mode
			return False

		# activate on repeated key
		if ((not text_mode) and self._key_pressed == keyv and
				keyv not in self.keys_sensible):
			if curtime - self._key_press_time > self._key_press_interval:
				self._activate(None, None)
				self._key_pressed = None
			return True
		else:
			self._key_press_time = curtime
			self._key_pressed = keyv


		if keyv not in self.keys_sensible:
			# exit if not handled
			return False
		self._reset_to_toplevel = False

		if keyv == key_book["Escape"]:
			self._escape_key_press()
			return True

		if keyv == key_book["Up"]:
			self.current.go_up()
		elif keyv == key_book["Down"]:
			if (not self.current.get_current() and
					self.current.get_match_state() is State.Wait):
				self._populate_search()
			self.current.go_down()
		elif keyv == key_book["Right"]:
			self._browse_down(alternate=mod1_mask)
		elif keyv == key_book["BackSpace"]:
			if not has_input:
				self._back_key_press()
			else:
				return False
		elif keyv == key_book["Left"]:
			self._back_key_press()
		elif keyv in (key_book["Tab"], key_book["ISO_Left_Tab"]):
			self.current.hide_table()
			self.switch_current(reverse=shift_mask)
		else:
			# cont. processing
			return False
		return True

	def _entry_paste_clipboard(self, entry):
		if not self.get_in_text_mode():
			self.try_enable_text_mode()

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
				self.emit("cancelled")
			self._reset_to_toplevel = True
			self.current.hide_table()
		self.reset_text()

	def _back_key_press(self):
		"""Handle leftarrow and backspace
		Go up back through browsed sources.
		"""
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
		if not self._theme_colors:
			return
		if self._is_text_mode:
			self.entry.set_size_request(-1,-1)
			self.entry.set_property("has-frame", True)
			bgcolor = gtk.gdk.color_parse("light goldenrod yellow")
			theme_entry_text = self._theme_colors["text"]
			self.entry.modify_text(gtk.STATE_NORMAL, theme_entry_text)
			self.entry.modify_base(gtk.STATE_NORMAL, bgcolor)
			self.current.set_state(gtk.STATE_ACTIVE)
		else:
			self.entry.set_size_request(0,0)
			self.entry.set_property("has-frame", False)
			theme_entry_bg = self._theme_colors["bg"]
			self.entry.modify_text(gtk.STATE_NORMAL, theme_entry_bg)
			self.entry.modify_base(gtk.STATE_NORMAL, theme_entry_bg)
			self.current.set_state(gtk.STATE_SELECTED)
		self._size_window_optimally()

	def switch_to_source(self):
		if self.current is not self.search:
			self.current = self.search
			self._update_active()
			if self.get_in_text_mode():
				self.toggle_text_mode_quick()

	def focus(self):
		"""called when the interface is focus (after being away)"""
		# preserve text mode, but switch to source if we are not in it
		if not self.get_in_text_mode():
			self.switch_to_source()
		# Check that items are still valid when "coming back"
		self.data_controller.validate()
		self._show_third_pane(self._pane_three_is_visible)

	def put_away(self):
		"""Called when the interface is hidden"""
		self._show_third_pane(False)
		self._relax_search_terms()
		self._reset_to_toplevel = True

	def select_selected_file(self):
		self.data_controller.find_object("qpfer:selectedtext")
		self.data_controller.find_object("qpfer:selectedfile")

	def select_selected_text(self):
		self.data_controller.find_object("qpfer:selectedtext")

	def _pane_reset(self, controller, pane, item):
		wid = self._widget_for_pane(pane)
		if not item:
			wid.reset()
		else:
			wid.set_match_plain(item)
			if wid is self.search:
				self.reset()
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
		if wid is self.current:
			self.toggle_text_mode(False)
			if not at_root:
				self.reset_current(populate=True)
				wid.show_table()
	
	def _show_hide_third(self, ctr, mode, ignored):
		gobject.source_remove(self._current_ui_transition)
		if mode is data.SourceActionObjectMode:
			# use a delay before showing the third pane,
			# but set internal variable to "shown" already now
			self._pane_three_is_visible = True
			self._current_ui_transition = \
					gobject.timeout_add(200, self._show_third_pane, True)
		else:
			self._pane_three_is_visible = False
			self._show_third_pane(False)

	def _show_third_pane(self, show):
		self._current_ui_transition = -1
		self.third.set_property("visible", show)
		self._size_window_optimally()

	def _size_window_optimally(self):
		"""Try to resize the window to its normal size"""
		if self.search.get_property("window"):
			win = self.search.get_toplevel()
			# size to minimum size
			win.resize(100, 50)
	
	def _update_active(self):
		self.action.set_active(self.action is self.current)
		self.search.set_active(self.search is self.current)
		self.third.set_active(self.third is self.current)
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
			self.toggle_text_mode(False)
			self._update_active()
	
	def _browse_up(self):
		pane = self._pane_for_widget(self.current)
		return self.data_controller.browse_up(pane)
	
	def _browse_down(self, alternate=False):
		pane = self._pane_for_widget(self.current)
		self.data_controller.browse_down(pane, alternate=alternate)

	def _activate(self, widget, current):
		# reset self through toggle_text_mode
		self.toggle_text_mode(False)
		self.data_controller.activate()
	
	def _search_result(self, sender, pane, matchrankable, matches, context):
		key = context
		wid = self._widget_for_pane(pane)
		wid.update_match(key, matchrankable, matches)

	def _widget_for_pane(self, pane):
		return self.pane_to_widget[pane]
	def _pane_for_widget(self, widget):
		return self.widget_to_pane[id(widget)]

	def _selection_changed(self, widget, match):
		pane = self._pane_for_widget(widget)
		self.data_controller.select(pane, match)
		if not widget is self.current:
			return
		self._description_changed()

	def _description_changed(self):
		match = self.current.get_current()
		name = match and match.get_description() or ""
		self.label.set_text(name)
	
	def _table_event(self, widget, table, event):
		self.entry.emit("key-press-event", event)

	def put_text(self, text):
		"""
		Put @text into the interface to search, to use
		for "queries" from other sources
		"""
		self.try_enable_text_mode()
		self.entry.set_text(text)
		self.entry.set_position(-1)

	def _changed(self, editable):
		"""
		The entry changed callback: Here we have to be sure to use
		**UNICODE** (unicode()) for the entered text
		"""
		# @text is UTF-8
		text = editable.get_text()
		text = text.decode("UTF-8")
		if not text:
			self.data_controller.cancel_search()
			# See if it was a deleting key press
			curev = gtk.get_current_event()
			if curev and curev.keyval in (self.key_book["Delete"],
					self.key_book["BackSpace"]):
				self._back_key_press()
			return

		pane = self._pane_for_widget(self.current)
		if not self.get_in_text_mode() and self._reset_to_toplevel:
			self.soft_reset(pane)

		self.data_controller.search(pane, key=text, context=text,
				text_mode=self.get_in_text_mode())

gobject.type_register(Interface)
gobject.signal_new("cancelled", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

class WindowController (pretty.OutputMixin):
	"""
	This is the fundamental Window (and App) Controller
	"""
	def __init__(self):
		"""
		"""
		gobject.set_prgname("kupfer")
		self.icon_name = gtk.STOCK_FIND
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

		data_controller = data.DataController()
		data_controller.connect("launched-action", self.launch_callback)

		self.interface = Interface(data_controller, self.window)
		self.interface.connect("cancelled", self._cancelled)
		self._setup_window()
		self._statusicon = None

	def show_statusicon(self):
		if not self._statusicon:
			self._statusicon = self._setup_status_icon()
		self._statusicon.set_visible(True)
	def hide_statusicon(self):
		if self._statusicon:
			self._statusicon.set_visible(False)

	def _settings_changed(self, setctl, section, key, value):
		if section == "Kupfer" and key == "showstatusicon":
			if value: self.show_statusicon()
			else: self.hide_statusicon()

	def _setup_status_icon(self):
		status = gtk.status_icon_new_from_stock(self.icon_name)
		status.set_tooltip(_("Kupfer"))

		def prefs_callback(menuitem):
			from kupfer import preferences
			preferences.GetPreferencesWindowController().show()
			return True
		def quit_callback(menuitem):
			self.quit()
			return True
		menu = gtk.Menu()
		menu_prefs = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
		menu_prefs.connect("activate", prefs_callback)
		menu_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
		menu_quit.connect("activate", quit_callback)
		menu.append(menu_prefs)
		menu.append(menu_quit)
		menu.show_all()

		status.connect("popup-menu", self._popup_menu, menu)
		status.connect("activate", self.show_hide)
		return status

	def _setup_window(self):
		"""
		Returns window
		"""
		self.window.connect("delete-event", self._close_window)
		widget = self.interface.get_widget()
		widget.show()
		
		self.window.add(widget)
		self.window.set_title(_("Kupfer"))
		self.window.set_icon_name(self.icon_name)
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
		self.window.set_keep_above(True)
		self.window.set_position(gtk.WIN_POS_CENTER)
		# This will change from utility window
		#self.window.set_resizable(False)

	def _popup_menu(self, status_icon, button, activate_time, menu):
		"""
		When the StatusIcon is right-clicked
		"""
		menu.popup(None, None, gtk.status_icon_position_menu, button, activate_time, status_icon)
	
	def launch_callback(self, sender, mode, leaf, action):
		# Separate window hide from the action being
		# done. This is to solve a window focus bug when
		# we switch windows using an action
		gobject.timeout_add(50,self.put_away)

	def activate(self, sender=None, time=0):
		evttime = time if time else gtk.get_current_event_time()
		self.window.stick()
		self.window.present_with_time(time)
		self.window.window.focus(timestamp=evttime)
		self.interface.focus()
	
	def put_away(self):
		self.interface.put_away()
		self.window.hide()
	
	def _cancelled(self, widget):
		self.put_away()
	
	def show_hide(self, sender=None, time=0):
		"""
		Toggle activate/put-away
		"""
		if self.window.get_property("visible"):
			self.put_away()
		else:
			self.activate(time=time)

	def _key_binding(self, keyobj, keybinding_number, event_time):
		"""Keybinding activation callback"""
		if keybinding_number == keybindings.KEYBINDING_MAGIC:
			self.activate(time=event_time)
			self.interface.select_selected_file()
		else:
			self.show_hide(time=event_time)

	def _put_text_recieved(self, sender, working_dir, text):
		"""We got a search query from dbus"""
		buildpath = os.path.join(working_dir, text)
		self.activate()
		if os.path.exists(buildpath):
			self.interface.put_text(buildpath)
		else:
			self.interface.put_text(text)

	def _close_window(self, window, event):
		self.put_away()
		return True

	def _destroy(self, widget, data=None):
		self.quit()
	
	def _sigterm(self, signal, frame):
		self.output_info("Caught signal", signal, "exiting..")
		self.quit()

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
		import signal
		from kupfer import session, settings

		self.output_debug("in lazy_setup")

		setctl = settings.GetSettingsController()
		if setctl.get_show_status_icon():
			self.show_statusicon()
		setctl.connect("value-changed", self._settings_changed)
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
		from kupfer import listen, scheduler

		try:
			kserv = listen.Service()
		except listen.AlreadyRunningError:
			self.output_info("An instance is already running, exiting...")
			self.quit_now()
		except listen.NoConnectionError:
			kserv = None
		else:
			kserv.connect("present", self.activate)
			kserv.connect("show-hide", self.show_hide)
			kserv.connect("put-text", self._put_text_recieved)
			kserv.connect("quit", self.quit)

		# Load data and present UI
		sch = scheduler.GetScheduler()
		sch.load()

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
