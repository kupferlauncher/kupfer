#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import itertools
import kupfer

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

class Search (gtk.Bin):
	"""
	A Widget for searching an matching

	Is connected to a kupfer.Search object

	Signals
	* cursor-changed: def callback(widget, selection)
		called with new selected (represented) object or None
	* key-pressed: def callback(widget, selection, keyval)
		called with selected (represented) object and keyval
		only called for certain keys, i.e right/left arrow
	* activate: def callback(widget, selection)
		called with activated leaf, when the widget is activated
		by typing enter, double clicking etc
	* cancelled: def callback(widget)
		called when the user cancels in the window (eg types Esc)
	"""
	__gtype_name__ = 'Search'
	def __init__(self):
		gobject.GObject.__init__(self)
		# object attributes
		self.model = LeafModel()
		self.search_object = None
		self.callbacks = {}
		self.match = None
		self.model_iterator = None
		# internal constants
		self.show_initial = 10
		self.show_more = 10
		self.label_char_width = 25
		# finally build widget
		self.build_widget()
	
	def build_widget(self):
		"""
		Core initalization method that builds the widget
		"""

		self.entry = gtk.Entry(max=0)
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate)
		self.entry.connect("key-press-event", self._entry_key_press)

		from pango import ELLIPSIZE_MIDDLE
		self.label = gtk.Label("<match>")
		self.label.set_justify(gtk.JUSTIFY_CENTER)
		self.label.set_width_chars(self.label_char_width)
		self.label.set_ellipsize(ELLIPSIZE_MIDDLE)
		self.icon_view = gtk.Image()

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

		# infobox: icon and match name
		infobox = gtk.HBox()
		infobox.pack_start(self.icon_view, True, True, 0)
		box = gtk.VBox()
		box.pack_start(infobox, False, False, 0)
		box.pack_start(self.label, True, True, 0)
		box.pack_start(self.entry, False, False, 0)
		self.add(box)
		box.show_all()
		self.__child = box

		self.list_window.add(self.scroller)
		self.scroller.show_all()

		self.set_focus_chain((self.entry,))

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
			self.emit("cancelled")
			return False

		path_at_row = lambda r: (r,)
		row_at_path = lambda p: p[0]

		# using (lazy and dangerous) tree path hacking here
		if keyv == uarrow:
			# go up, simply. close table if we go up from row 0
			path, col = self.table.get_cursor()
			if path:
				r = row_at_path(path)
				if r >= 1:
					self.table.set_cursor(path_at_row(r-1))
				else:
					self._hide_table()
		elif keyv == darrow:
			# if no data is loaded (frex viewing catalog), load
			# if too little data is loaded, try load more
			if self.search_object and not len(self.model):
				self.init_table(self.show_initial)
			if self.model_iterator and len(self.model) <= 1:
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
		elif keyv in (larrow, rarrow, backsp):
			if (keyv == rarrow and self.match):
				self.emit("key-pressed", self.match, keyv)
			elif keyv in (larrow, backsp):
				# larrow or backspace will erase or go up
				if not self.match:
					self.emit("key-pressed", self.match, larrow)
				else:
					self.reset()
				self.entry.set_text("")
				self._hide_table()
		else:
			if keyv == tabkey:
				self._hide_table()
			return False

		path, col = self.table.get_cursor()
		if path:
			self.set_match(self.model.get_object(path))

		# stop further processing
		return True
	
	def _table_key_press(self, treeview, event):
		"""
		Catch keypresses in the treeview and divert them
		"""
		self.entry.grab_focus()
		self.entry.emit("key-press-event", event)
		return True
	
	def get_current(self):
		"""
		return current selection
		"""
		return self.match

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
		wid, hei = self.window.get_size()
		pos_x, pos_y = self.window.get_position()
		lowerc = pos_y + hei
		self.list_window.move(pos_x, lowerc)
		self.list_window.resize(wid, 200)
		self.list_window.show()
	
	def _window_config(self, widget, event):
		if self._get_table_visible():
			self._hide_table()
			gobject.timeout_add(300, self._show_table)

	def _get_cur_object(self):
		"""
		FIXME: Should this not be gone and use get_current?
		"""
		path, col = self.table.get_cursor()
		if not path:
			return None
		return self.model.get_object(path)

	def _activate(self, entry):
		obj = self.match
		self.emit("activate", obj)
	
	def _row_activated(self, treeview, path, col):
		obj = self._get_cur_object()
		self.emit("activate", obj)

	def _cursor_changed(self, treeview):
		path, col = treeview.get_cursor()
		if not path:
			self.emit("cursor-changed", None)
			return
		self.set_match(self.model.get_object(path))
		self.update_match()
	
	def set_match(self, match):
		"""
		Set the currently selected (represented) object
		
		Emits cursor-changed
		"""
		self.match = match
		self.emit("cursor-changed", self.match)

	def reset(self):
		self.entry.set_text("")
		self.label.set_text("Type to search")
		self.icon_view.clear()
		self.model.clear()
		self.setup_empty()
	
	def setup_empty(self):
		self.set_match(None)

	def init_table(self, num=None):
		"""
		Fill table with entries
		and set match to first entry
		"""
		self.model_iterator = iter(self.search_object.search_base)
		first = self.populate_model(self.model_iterator, num)
		self.set_match(first)
		if first:
			self.update_match()
	
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

	def do_search(self, text):
		"""
		return the best items
		"""
		self.model.clear()
		matches = self.search_object.search_objects(text)
		self.model_iterator = iter(matches)
		if not len(matches):
			self.handle_no_matches()
			return None
		
		# get the best object
		top = self.populate_model(self.model_iterator, 1)
		return top
	
	def _changed(self, editable):
		text = editable.get_text()
		if not len(text):
			return
		if not self.search_object:
			return
		match = self.do_search(text)
		if match:
			self.set_match(match)
			self.update_match()
		self._hide_table()

	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		# update icon
		icon = self.match.get_icon()
		if icon:
			self.icon_view.set_from_pixbuf(icon)
		else:
			self.icon_view.clear()

		# update text label
		def escape(c):
			"""
			Escape char for markup (use unicode)
			"""
			table = {u"&": u"&amp;", u"<": u"&lt;", u">": u"&gt;" }
			if c in table:
				return table[c]
			return c
		
		def markup_match(key, match):
			"""
			Return escaped and ascii-encoded markup string
			"""
			from codecs import getencoder
			encoder = getencoder('us-ascii')
			encode_char = lambda c: encoder(c, 'xmlcharrefreplace')[0]

			markup = u""
			idx = 0
			open, close = (u"<u>", u"</u>")
			for n in match_str:
				if idx < len(key) and n.lower() == key[idx]:
					idx += 1
					markup += (open + escape(n) + close)
				else:
					markup += (escape(n))
			# simplify
			# compare to T**2 = S.D**2.inv(S)
			markup = markup.replace(close + open, u"")
			markup = encode_char(markup)
			return markup
		
		text = unicode(self.entry.get_text())
		match_str = unicode(self.match)
		key = kupfer.remove_chars_unicode(text.lower(), " _-.")
		markup = markup_match(key, match_str)
		self.label.set_markup(markup)

	def set_search_object(self, obj):
		self.search_object = obj
		self.reset()
	
	def set_no_match(self, text, icon):
		dim_icon = icon.copy()
		icon.saturate_and_pixelate(dim_icon, 0.3, False)
		self.set_match(None)
		self.label.set_text(text)
		self.icon_view.set_from_pixbuf(dim_icon)
	
	def handle_no_matches(self):
		pass


# Take care of gobject things to set up the Search class
gobject.type_register(Search)
gobject.signal_new("activate", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("key-pressed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_INT, ))
gobject.signal_new("cursor-changed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("cancelled", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

class LeafSearch (Search):
	"""
	Customize for leaves search	
	"""
	def set_source(self, source):
		"""
		Use source as the new leaf source
		"""
		self.source = source
		self.set_search_object(self.make_searchobj(source))
		self.model_iterator = None
		self._hide_table()

	def make_searchobj(self, source):
		leaves = source.get_leaves() 
		return kupfer.Search(((leaf.value, leaf) for leaf in leaves))

	def setup_empty(self):
		icon = self.source.get_icon()
		self.icon_view.set_from_pixbuf(icon)

		title = "Searching %s..." % self.source
		self.label.set_text(title)
		self.set_match(None)
		# violently grab focus -- we are the prime focus
		self.entry.grab_focus()

	def handle_no_matches(self):
		from objects import DummyLeaf
		dum = DummyLeaf()
		self.set_no_match(str(dum), dum.get_icon())


class ActionSearch (Search):
	"""
	Customization for Actions
	"""
	def setup_empty(self):
		if self.search_object:
			self.init_table()
			if self.match:
				return
		self.handle_no_matches()
		self._hide_table()
	
	def handle_no_matches(self):
		from objects import DummyAction
		dum = DummyAction()
		self.set_no_match(str(dum), dum.get_icon())

class Browser (object):
	def __init__(self, datasource):
		"""
		"""
		self.window = self._setup_window()
		self.source_stack = []
		self.push_source(datasource)
		self.refresh_data()

	def _setup_window(self):
		"""
		Returns window
		"""
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.connect("destroy", self._destroy)
		
		self.leaf_search = LeafSearch()
		self.leaf_search.connect("activate", self._activate_object)
		self.leaf_search.connect("key-pressed", self._key_press)
		self.leaf_search.connect("cursor-changed", self._cursor_changed)
		self.leaf_search.connect("cancelled", self._search_cancelled)

		self.action_search = ActionSearch()
		self.action_search.connect("activate", self._activate_action)
		self.action_search.connect("cancelled", self._search_cancelled)

		window.connect("configure-event", self.leaf_search._window_config)
		window.connect("configure-event", self.action_search._window_config)

		box = gtk.HBox()
		box.pack_start(self.leaf_search, True, True, 0)
		box.pack_start(self.action_search, True, True, 0)
		self.leaf_search.show()
		self.action_search.show()
		box.show()
		window.add(box)
		window.show()
		window.set_title("Kupfer")
		return window

	def source_rebase(self, src):
		self.source_stack = []
		self.push_source(src)
		self.refresh_data()
	
	def push_source(self, src):
		self.source = src
		#self.source.set_refresh_callback(self.refresh_data)
		self.source_stack.insert(0, src)
	
	def pop_source(self):
		if len(self.source_stack) <= 1:
			raise Exception
		else:
			self.source_stack.pop(0)
			self.source = self.source_stack[0]
	
	def refresh_data(self):
		self.leaf_search.set_source(self.source)

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	def _cursor_changed(self, widget, leaf):
		"""
		Selected item changed in Leaves widget

		Updates the Actions widget
		"""
		if not leaf:
			sobj = None
		else:
			actions = leaf.get_actions()
			sobj = kupfer.Search(((str(act), act) for act in actions))
		self.action_search.set_search_object(sobj)
	
	def _key_press(self, widget, leaf, keyval):
		"""
		Handle key presses:
		Right arrow - go into object
		Left arrow - go to parent
		"""
		rightarrow = 0xFF53
		leftarrow = 0xFF51
		if keyval == rightarrow:
			if not leaf.has_content():
				return
			self.push_source(leaf.content_source())
			
		elif keyval == leftarrow:
			try:
				self.pop_source()
			except:
				if self.source.has_parent():
					self.source_rebase(self.source.get_parent())
		else:
			return
		self.refresh_data()
	
	def _search_cancelled(self, widget):
		try:
			while True:
				self.pop_source()
		except:
			self.refresh_data()


	def _activate_action(self, widget, action):
		leaf = self.leaf_search.get_current()
		self.eval_action(action, leaf)
	
	def _activate_object(self, widget, leaf):
		action = self.action_search.get_current()
		self.eval_action(action, leaf)
	
	def eval_action(self, action, leaf):
		"""
		Evaluate an action with the given leaf
		"""
		if not action or not leaf:
			print "No action", (action, leaf)
			return
		new_source = action.activate(leaf)
		# handle actions returning "new contexts"
		if action.is_factory() and new_source:
			self.push_source(new_source)
			self.refresh_data()

	def main(self):
		gtk.main()

