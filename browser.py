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

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("item", cell)
		nbr_col = gtk.TreeViewColumn("rank", cell)

		col.add_attribute(cell, "text", self.val_col)
		nbr_col.add_attribute(cell, "text", self.rank_col)
		self.columns = (col, nbr_col)

	def add(self, tupl):
		leaf, rank = tupl
		self.append((leaf, str(leaf), rank))

class Search (gtk.Bin):
	"""
	A Widget for searching an matching

	Is connected to a kupfer.Search object

	Signals
	* cursor-changed: def callback(selection)
		called with new selected (represented) object or None
	* key-pressed: def callback(selection, keyval)
		called with selected (represented) object and keyval
		only called for certain keys, i.e right/left arrow
	* activate: def callback(selection)
		called with activated leaf, when the widget is activated
		by typing enter, double clicking etc
	"""
	__gtype_name__ = 'Search'
	def __init__(self):
		gobject.GObject.__init__(self)
		self.model = LeafModel()
		self.search_object = None
		self.callbacks = {}
		self.match = None

		self.entry = gtk.Entry(max=0)
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate)
		self.entry.connect("key-press-event", self._entry_key_press)

		self.label = gtk.Label("<match>")
		self.label.set_justify(gtk.JUSTIFY_LEFT)
		self.icon_view = gtk.Image()

		self.table = gtk.TreeView(self.model.store)
		self.table.set_headers_visible(False)

		for col in self.model.columns:
			self.table.append_column(col)

		self.table.connect("row-activated", self._row_activated)
		self.table.connect("key-press-event", self._key_press)
		self.table.connect("cursor-changed", self._cursor_changed)

		# infobox: icon and match name
		infobox = gtk.HBox()
		infobox.pack_start(self.icon_view, False, False, 0)
		infobox.pack_start(self.label, False, False, 0)
		box = gtk.VBox()
		box.pack_start(infobox, False, False, 0)
		box.pack_start(self.entry, False, False, 0)
		box.pack_start(self.table, True, True, 0)
		self.add(box)
		box.show_all()
		self.table.hide()
		self.__child = box

		self.set_focus_chain((self.entry,))
	
	def _entry_key_press(self, entry, event):
		"""
		Intercept arrow keys and manipulate table
		without losing focus from entry field
		"""
		keyv = event.keyval
		uarrow = 65362
		darrow = 65364
		rarrow = 65363
		larrow = 65361
		tabkey = 65289

		path_at_row = lambda r: (r,)

		# using (lazy and dangerous) tree path hacking here
		if keyv in (uarrow, darrow):
			if len(self.model) > 1:
				path, col = self.table.get_cursor()
				old_sel = path
				if not path and keyv == darrow:
					path = path_at_row(0)
					self.table.set_cursor(path)
				elif path:
					r, = path
					if keyv == darrow: r +=  1
					else: r -= 1
					r = r % len(self.model)
					self.table.set_cursor(path_at_row(r))
				sel, col = self.table.get_cursor()
				if old_sel != sel:
					self.table.show()
		elif keyv in (larrow, rarrow):
			if keyv == larrow or self.match:
				self.emit("key-pressed", self.match, keyv)
		else:
			if keyv == tabkey:
				self._hide_table()
			return False

		path, col = self.table.get_cursor()
		if path:
			self.set_match(self.model.get_object(path))

		# stop further processing
		return True

	def get_current(self):
		return self.match

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)
	
	def _hide_table(self):
		self.table.hide()
		# make the window minimal again
		window = self.get_toplevel()
		window.resize(1,1)

	def _get_cur_object(self):
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

	def _key_press(self, treeview, event):
		obj = self._get_cur_object()
		self.emit("key-pressed", obj, event.keyval)
	
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
		first = None
		for item in itertools.islice(self.search_object.search_base, 10):
			self.model.add((item.object, 0))
			if not first: first = item.object
		if first:
			self.set_match(first)
			self.update_match()


	def do_search(self, text):
		"""
		return the best items
		"""
		# print "Type in search string"
		# in_str = raw_input()
		ranked_str = self.search_object.search_objects(text)

		self.model.clear()
		for s in itertools.islice(ranked_str, 10):
			row = (s.object, s.rank)
			self.model.add(row)
		top = ranked_str[0]
		# top.object is a leaf
		return top.object
	
	def _changed(self, editable):
		text = editable.get_text()
		if not len(text):
			self.set_match(None)
			return
		self.set_match(self.do_search(text))
		self.update_match()
		self._hide_table()

	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		print "Marking", self.match

		# update icon
		icon = self.match.get_pixbuf()
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
		print markup
		self.label.set_markup(markup)

	def set_search_object(self, obj):
		self.search_object = obj
		self.reset()

# Take care of gobject things to set up the Search class
gobject.type_register(Search)
gobject.signal_new("activate", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("key-pressed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_INT, ))
gobject.signal_new("cursor-changed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))

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

	def make_searchobj(self, source):
		leaves = source.get_leaves() 
		return kupfer.Search(((leaf.value, leaf) for leaf in leaves))

	def setup_empty(self):
		self.icon_view.set_from_pixbuf(self.source.get_pixbuf())
		self.table.hide()
		self.label.set_text("(%s)" % self.source)


class ActionSearch (Search):
	pass


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
		
		self.action_search = Search()
		self.action_search.connect("activate", self._activate_action)

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
		self.refresh_data()
	
	def pop_source(self):
		if len(self.source_stack) <= 1:
			raise
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
		new_source = action.activate(leaf)
		# handle actions returning "new contexts"
		if action.is_factory() and new_source:
			self.push_source(new_source)
			self.refresh_data()

	def main(self):
		gtk.main()


