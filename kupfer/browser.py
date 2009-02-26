#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import itertools
from . import kupfer

# State Constants
class State (object):
	Wait, Match, NoMatch = (1,2,3)

class ModelBase (object):
	def __init__(self, *columns):
		"""
		First column is always the object -- returned by get_object
		it needs not be specified in columns
		"""
		self.store = gtk.ListStore(gobject.TYPE_PYOBJECT, *columns)
		self.object_column = 0
	
	def __len__(self):
		return len(self.store)

	def _get_column(self, treepath, col):
		iter = self.store.get_iter(treepath)
		val = self.store.get_value(iter, col)
		return val
	
	def get_object(self, path):
		return self._get_column(path, self.object_column)

	def append(self, row):
		self.store.append(row)

	def clear(self):
		self.store.clear()

class LeafModel (ModelBase):
	def __init__(self):
		ModelBase.__init__(self, str, int)
		self.val_col = 1
		self.rank_col = 2

		from pango import ELLIPSIZE_MIDDLE
		cell = gtk.CellRendererText()
		cell.set_property("ellipsize", ELLIPSIZE_MIDDLE)
		cell.set_property("width-chars", 50)
		col = gtk.TreeViewColumn("item", cell)

		nbr_cell = gtk.CellRendererText()
		nbr_cell.set_property("width-chars", 4)
		nbr_col = gtk.TreeViewColumn("rank", nbr_cell)

		col.add_attribute(cell, "text", self.val_col)
		nbr_col.add_attribute(nbr_cell, "text", self.rank_col)
		self.columns = (col, nbr_col)

	def add(self, tupl):
		leaf, rank = tupl
		self.append((leaf, str(leaf), rank))

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
		self.match_state = State.Wait
		# finally build widget
		self.build_widget()
		self.cur_icon = None
		self.cur_text = None
		self.cur_match = None

		# Get the current selection color
		ent = gtk.Entry()
		newc = ent.style.bg[3]
		self.event_box.modify_bg(gtk.STATE_SELECTED, newc)

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
		box.pack_start(infobox, False, False, 0)
		box.pack_start(self.label, True, True, 0)
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
			self.icon_view.clear()

		if not self.cur_text:
			self.label.set_text("<no text>")
			return
		
		if not self.cur_match or self.match_state is not State.Match:
			self.label.set_text(self.cur_text)
			return

		# update the text label
		def markup_match(key, text):
			"""
			Return escaped and ascii-encoded markup string for gtk.Label

			Use unicode's method .encode to encode in ascii and use xml
			entities for unicode chars. Use a simeple homegrown replace table
			to replace &, <, > with entities before adding markup.
			"""
			encode = lambda c: c.encode('us-ascii', 'xmlcharrefreplace')
			escape_table = {u"&": u"&amp;", u"<": u"&lt;", u">": u"&gt;" }
			escape = lambda c: escape_table.get(c, c)
			open, close = (u"<b>", u"</b>")

			def lower_partition(text, key):
				"""do str.partition, but partition case-insensitively"""
				head, sep, tail = text.lower().partition(key)
				head, sep = text[:len(head)], text[len(head):len(head)+len(sep)]
				if len(tail):
					tail = text[-len(tail):]
				return head, sep, tail

			def rmarkup(key, text):
				if not key:
					return text
				"""recursively find search string in match"""
				if key in text.lower():
					nextkey=None
				else:
					key, nextkey = key[0], key[1:]
				head, sep, tail = lower_partition(text, key)
				return head + open + sep + close + rmarkup(nextkey, tail)

			markup = rmarkup(key,text)
			# simplify
			# compare to T**2 = S.D**2.inv(S)
			markup = markup.replace(close + open, u"")
			markup = encode(markup)
			return markup
		
		text = unicode(self.cur_text)
		match = unicode(self.cur_match)
		key = u"".join(c for c in match.lower() if c not in " _-.")
		markup = markup_match(key, text)
		self.label.set_markup(markup)
	
	@classmethod
	def _dim_icon(cls, icon):
		if icon:
			dim_icon = icon.copy()
			icon.saturate_and_pixelate(dim_icon, 0.3, False)
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
	A Widget for searching an matching

	Is connected to a kupfer.Search object

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
		self.callbacks = {}
		self.match = None
		self.model_iterator = None
		self.match_state = State.Wait
		self.text = ""
		# internal constants
		self.show_initial = 10
		self.show_more = 10
		self.label_char_width = 25
		# finally build widget
		self.build_widget()
		self.setup_empty()
	
	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""
		self.match_view = MatchView()

		self.table = gtk.TreeView(self.model.store)
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

		self.list_window = gtk.Window()
		self.list_window.set_decorated(False)
		self.list_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_UTILITY)

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

	def get_match_state(self):
		return self.match_state

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)
	
	def _get_table_visible(self):
		return self.list_window.get_property("visible")

	def _hide_table(self):
		self.list_window.hide()

	def _show_table(self):
		win_width, win_height = self.window.get_size()
		pos_x, pos_y = self.window.get_position()
		lowerc = pos_y + win_height
		table_w, table_len = self.table.size_request()
		subwin_height = min(table_len, 200)
		self.list_window.move(pos_x, lowerc)
		self.list_window.resize(win_width, subwin_height)
		self.list_window.show()
	
	# table methods
	def go_up(self):
		"""
		Upwards in the table
		"""
		# using (lazy and dangerous) tree path hacking here
		path_at_row = lambda r: (r,)
		row_at_path = lambda p: p[0]

		# go up, simply. close table if we go up from row 0
		path, col = self.table.get_cursor()
		if path:
			r = row_at_path(path)
			if r >= 1:
				self.table.set_cursor(path_at_row(r-1))
			else:
				self._hide_table()
	
	def go_down(self):
		"""
		Down in the table
		"""
		# using (lazy and dangerous) tree path hacking here
		path_at_row = lambda r: (r,)
		row_at_path = lambda p: p[0]

		# if no data is loaded (frex viewing catalog), load
		# if too little data is loaded, try load more
		if not len(self.model):
			self.init_table(self.show_initial)
		if len(self.model) <= 1:
			self.populate_model(self.model_iterator, self.show_more)
		if len(self.model) > 1:
			path, col = self.table.get_cursor()
			if path:
				r = row_at_path(path)
				if r == -1 + len(self.model):
					self.populate_model(self.model_iterator, self.show_more)
				if r < -1 + len(self.model):
					self.table.set_cursor(path_at_row(r+1))
			else:
				self.table.set_cursor(path_at_row(0))
			self._show_table()
	
	def _window_config(self, widget, event):
		"""
		When the window moves
		"""
		if self._get_table_visible():
			self._hide_table()
			gobject.timeout_add(300, self._show_table)
	
	def _window_hidden(self, window):
		"""
		Window changed hid
		"""
		self._hide_table()

	def _row_activated(self, treeview, path, col):
		obj = self.get_current()
		self.emit("activate", obj)

	def _cursor_changed(self, treeview):
		path, col = treeview.get_cursor()
		match = self.model.get_object(path)
		self.set_match(match)
	
	def set_match(self, match):
		"""
		Set the currently selected (represented) object

		Emits cursor-changed
		"""
		print "Set match to", match
		self.match = match
		self.emit("cursor-changed", self.match)
		if match:
			self.match_state = State.Match
			self.match_view.set_match_state(str(self.match), self.match.get_icon(), match=self.text, state=self.match_state)

	def update_match(self, key, matchrankable, matches):
		"""
		@matchrankable: Rankable first match or None
		@matches: Iterable to rest of matches
		"""
		self.model.clear()
		if not matchrankable:
			self.set_match(None)
			return self.handle_no_matches()
		match = matchrankable.object
		self.set_match(match)
		self.text = key
		self.model_iterator = iter(matches)
		top = self.populate_model(self.model_iterator, 1)
		print top

	def reset(self):
		self.model.clear()
		self.setup_empty()
	
	def setup_empty(self):
		self.match_state = State.NoMatch
		self.match_view.set_match_state("No match", None, state=State.NoMatch)

	def init_table(self, num=None):
		"""
		Fill table with entries
		and set match to first entry
		"""
		#self.model_iterator = #iter(self.search_object.search_base)
		first = self.populate_model(self.model_iterator, num)
		self.set_match(first)
	
	def populate_model(self, iterator, num=None):
		"""
		populate model with num items from iterator

		and return first item inserted
		if num is none, insert everything
		"""
		if num:
			iterator = itertools.islice(iterator, num)
		first = None
		for item in iterator:
			row = (item.object, item.rank)
			self.model.add(row)
			if not first: first = item.object
		# first.object is a leaf
		return first
	
	def handle_no_matches(self):
		pass
	
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

class Interface (gobject.GObject):
	"""
	Controller object that controls the input and
	the state (current active) search object/widget

	Signals:
	* activate: def callback(controller, leaf, action)
	* cancelled: def callback(controller)
		escape was typed
	* browse-up
		leftarrow/backspace used to go up
	* browse-down
		rightarrow: try to go down in hierarchy
	"""
	__gtype_name__ = "Interface"

	def __init__(self, controller, entry, label, search, action, window):
		"""
		@controller: DataController
		@entry: gtk.Entry
		@search: source search controller
		@action: action search controller
		@window: toplevel window
		"""
		gobject.GObject.__init__(self)
		self.entry = entry
		self.search = search
		self.action = action
		self.current = None

		from pango import ELLIPSIZE_END
		self.label = label
		self.label.set_width_chars(50)
		self.label.set_ellipsize(ELLIPSIZE_END)

		self.switch_to_source()
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate, None)
		self.entry.connect("key-press-event", self._entry_key_press)
		self.search.connect("table-event", self._table_event)
		self.action.connect("table-event", self._table_event)
		self.search.connect("activate", self._activate)
		self.action.connect("activate", self._activate)
		self.search.connect("cursor-changed", self._search_match_changed)
		self.search.connect("cursor-changed", self._selection_changed)
		self.action.connect("cursor-changed", self._selection_changed)
		window.connect("configure-event", self.search._window_config)
		window.connect("configure-event", self.action._window_config)
		window.connect("hide", self.search._window_hidden)
		window.connect("hide", self.action._window_hidden)
		self.data_controller = controller
		self.data_controller.connect("search-result", self._search_result)
		self.data_controller.connect("predicate-result", self._predicate_result)


	def _entry_key_press(self, entry, event):
		"""
		Intercept arrow keys and manipulate table
		without losing focus from entry field
		"""
		keyv = event.keyval
		sensible = (uarrow, darrow, rarrow, larrow,
				tabkey, backsp, esckey) = (65362, 65364, 65363,
				65361, 65289, 65288, 65307)

		if keyv not in sensible:
			# exit if not handled
			return False

		if keyv == esckey:
			self.emit("cancelled", self.search.match_state)
			self.reset()
			self.switch_to_source()
			return False

		if keyv == uarrow:
			self.current.go_up()
		elif keyv == darrow:
			self.current.go_down()
		elif keyv in (larrow, rarrow, backsp):
			match = self.search.get_current()
			if (keyv == rarrow and match):
				self._browse_down(match)
			elif keyv in (larrow, backsp):
				# larrow or backspace will erase or go up
				if not match and self.search.get_match_state() is State.Wait:
					self._browse_up(match)
				else:
					self.current.reset()
				self.entry.set_text("")
				self.current._hide_table()
		else:
			if keyv == tabkey:
				self.current._hide_table()
				self.switch_current()
			return False
	
		# stop further processing
		return True

	def reset(self):
		self.entry.set_text("")
		self.current._hide_table()
	
	def switch_to_source(self):
		if self.current is not self.search:
			self.current = self.search
			self._update_active()
	
	def _update_active(self):
		self.action.set_active(self.action is self.current)
		self.search.set_active(self.search is self.current)
		self._description_changed()

	def switch_current(self):
		if self.current is self.search:
			self.current = self.action
		else:
			self.current = self.search
		self._update_active()
		self.reset()
	
	def _browse_up(self, match):
		self.emit("browse-up", match)
		self.reset()
	
	def _browse_down(self, match):
		self.emit("browse-down", match)
		self.reset()

	def _activate(self, widget, current):
		act = self.action.get_current()
		obj = self.search.get_current()
		self.emit("activate", obj, act)
		self.reset()
	
	def _search_result(self, sender, matchrankable, matches, context):
		print "Got result", matchrankable, "for ctx", context
		self.switch_to_source()
		key = context
		self.search.update_match(key, matchrankable, matches)

	def _predicate_result(self, sender, matchrankable, matches, context):
		print "Got predicate", matchrankable, "for ctx", context
		key = context
		self.action.update_match(key, matchrankable, matches)

	def _search_match_changed(self, widget, match):
		print "_search_match_changed"
		if match:
			self.data_controller.search_predicate(match)
		else:
			self.action.update_match(None, None, None)

	def _selection_changed(self, widget, match):
		if not widget is self.current:
			return
		self._description_changed()

	def _description_changed(self):
		match = self.current.get_current()
		name = match and match.get_description() or ""
		self.label.set_text(name)
	
	def _table_event(self, widget, table, event):
		self.entry.emit("key-press-event", event)
	
	def _changed(self, editable):
		text = editable.get_text()
		if not len(text):
			return
		if self.current is self.search:
			self.data_controller.search(text, context=text)
		else:
			self.data_controller.search_predicate(self.search.get_current(), text, context=text)

gobject.type_register(Interface)
gobject.signal_new("activate", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))
gobject.signal_new("cancelled", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))
gobject.signal_new("browse-up", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))
gobject.signal_new("browse-down", Interface, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class LeafSearch (Search):
	"""
	Customize for leaves search	
	"""
	def setup_empty(self):
		from objects import DummyLeaf
		dum = DummyLeaf()
		icon = dum.get_icon()

		title = "Searching..."
		self.set_match(None)
		self.match_state = State.Wait
		self.match_view.set_match_state(title, icon, state=State.Wait)

	def handle_no_matches(self):
		from objects import DummyLeaf
		dum = DummyLeaf()
		self.match_state = State.NoMatch
		self.match_view.set_match_state(str(dum), dum.get_icon(), state=State.NoMatch)


class ActionSearch (Search):
	"""
	Customization for Actions
	"""
	def setup_empty(self):
		self.handle_no_matches()
		self._hide_table()
	
	def handle_no_matches(self):
		from objects import DummyAction
		dum = DummyAction()
		self.match_view.set_match_state(str(dum), dum.get_icon(), state=State.NoMatch)
		self.match_state = State.NoMatch

from .data import DataController

class WindowController (object):
	"""
	This is the fundamental Window (and App) Controller
	"""
	def __init__(self, datasource):
		"""
		"""
		self.icon_name = gtk.STOCK_FIND
		self.data_controller = DataController(datasource)
		self.window = self._setup_window()
		self._setup_status_icon()
		self.interface.connect("activate", self.data_controller._activate)
		self.interface.connect("browse-down", self.data_controller._browse_down)
		self.interface.connect("browse-up", self.data_controller._browse_up)
		self.interface.connect("cancelled", self.data_controller._search_cancelled)
		self.interface.connect("cancelled", self._cancelled)
		self.data_controller.connect("launched-action", self.launch_callback)
		self.activate()

	def _setup_status_icon(self):
		status = gtk.status_icon_new_from_stock(self.icon_name)
		status.set_tooltip("Kupfer")

		menu = gtk.Menu()
		menu_quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
		menu_quit.connect("activate", self._destroy)
		menu.append(menu_quit)
		menu.show_all()

		status.connect("popup-menu", self._popup_menu, menu)
		status.connect("activate", self._show_hide)

	def _setup_window(self):
		"""
		Returns window
		"""
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.connect("delete-event", self._close_window)
		
		self.leaf_search = LeafSearch()
		self.action_search = ActionSearch()

		entry = gtk.Entry()
		label = gtk.Label()
		self.interface = Interface(self.data_controller, entry, label,
				self.leaf_search, self.action_search, window)

		box = gtk.HBox()
		box.pack_start(self.leaf_search, True, True, 0)
		box.pack_start(self.action_search, True, True, 0)
		vbox = gtk.VBox()
		vbox.pack_start(box, True, True, 0)
		vbox.pack_start(label, True, True, 0)
		vbox.pack_start(entry, True, True, 0)
		vbox.show_all()
		window.add(vbox)
		window.set_title("Kupfer")
		window.set_icon_name(self.icon_name)
		return window

	def _popup_menu(self, status_icon, button, activate_time, menu):
		"""
		When the StatusIcon is right-clicked
		"""
		menu.popup(None, None, gtk.status_icon_position_menu, button, activate_time, status_icon)
	
	def launch_callback(self, sender, leaf, action):
		self.put_away()
	
	def activate(self):
		self.window.set_keep_above(True)
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.present()
		self.window.window.focus()
		self.interface.switch_to_source()
	
	def put_away(self):
		self.window.hide()
	
	def quit(self):
		gtk.main_quit()
	
	def _cancelled(self, widget, state):
		if state is State.Wait:
			self.put_away()
	
	def _show_hide(self, status_icon):
		"""
		When the StatusIcon is clicked
		"""
		if self.window.is_active():
			self.put_away()
		else:
			self.activate()
	
	def _close_window(self, window, event):
		self.put_away()
		return True

	def _destroy(self, widget, data=None):
		self.quit()

	def main(self):
		# register dbus callbacks
		import listen
		listen.register("activate", self.activate)
		listen.register("quit", self.quit)
		try:
			gtk.main()
		except KeyboardInterrupt, info:
			print info, "exiting.. (Warning: Ctrl-C in the shell will",\
					"kill child processes)"
			raise SystemExit

