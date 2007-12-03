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
	
	def get_value(self, treepath):
		"""
		Return model's value for treeview's path
		"""
		return self._get_column(treepath, self.val_col)

	def get_rank(self, treepath):
		"""
		Return model's rank for the treeview path
		"""
		return self._get_column(treepath, self.rank_col)

	def add(self, tupl):
		leaf, rank = tupl
		self.append((leaf, leaf.value, rank))


class ActionModel (ModelBase):
	def __init__(self):
		ModelBase.__init__(self, str, int )
		self.name_col, self.rank_col = 1,2
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Action", cell)
		col.add_attribute(cell, "text", self.name_col)
		col2 = gtk.TreeViewColumn("", cell)
		col2.add_attribute(cell, "text", self.rank_col)
		self.columns = (col, col2)
	
	def get_name(self, path):
		return self._get_column(path, self.name_col)
	
	def add(self, tupl):
		act, rank = tupl
		self.append((act, str(act), rank))

class Search (gtk.Bin):
	__gtype_name__ = 'Search'
	def __init__(self, model):
		gobject.GObject.__init__(self)
		self.model = model
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

		if keyv in (uarrow, darrow):
			path, col = self.table.get_cursor()
			if not path:
				if keyv == darrow:
					r = 0
				else:
					r = len(self.model)-1
				path = path_at_row(r)
				self.table.set_cursor(path)
			else:
				r, = path
				if keyv == darrow: r +=  1
				else: r -= 1
				r = r % len(self.model)
				self.table.set_cursor(path_at_row(r))
			self.table.show_all()
		elif keyv in (larrow, rarrow):
			path, col = self.table.get_cursor()
			if not path:
				path = path_at_row(0)
			obj = self.model.get_object(path)
			self.emit("key-pressed", obj, keyv)
		else:
			if keyv == tabkey:
				self._hide_table()
			return False

		path, col = self.table.get_cursor()
		if not path: path = path_at_row(0)
		self.match = self.model.get_object(path)
		self.emit("cursor-changed", self.match)

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
		self.match = self.model.get_object(path)
		self.update_match()
		self.emit("cursor-changed", self.match)

	def reset(self):
		self.entry.set_text("")
		self.label.set_text("Type to search")
		self.icon_view.clear()
		self.model.clear()
		first = None
		for item in itertools.islice(self.search_object.search_base, 10):
			self.model.add((item.object, 0))
			if not first: first = item.object
		if first:
			self.match = first
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
			self.match = None
			return
		self.match = self.do_search(text)
		self.update_match()
		self.emit("cursor-changed", self.match)
		self._hide_table()
	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		text = self.entry.get_text()
		print "Marking", self.match
		# update icon
		icon = self.match.get_pixbuf()
		if icon:
			self.icon_view.set_from_pixbuf(icon)
		else:
			self.icon_view.clear()

		#update text label
		markup = ""
		idx = 0
		from xml.sax.saxutils import escape
		key = kupfer.remove_chars(text.lower(), " _-.")
		for n in str(self.match):
			if idx < len(key) and n.lower() == key[idx]:
				idx += 1
				markup += ("<u>"+ escape(n) + "</u>")
			else:
				markup += (escape(n))
		self.label.set_markup(markup)

	def set_search_object(self, obj):
		self.search_object = obj
		self.reset()

gobject.type_register(Search)
gobject.signal_new("activate", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))
gobject.signal_new("key-pressed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_INT, ))
gobject.signal_new("cursor-changed", Search, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, ))

class Browser (object):
	def __init__(self, datasource):
		"""
		"""
		self.model = LeafModel()
		self.actions_model = ActionModel()
		self.source_stack = []
		self.push_source(datasource)
		self.window = self._setup_window()
		self.refresh_data()

	def _setup_window(self):
		"""
		Returns window
		"""
		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.connect("destroy", self._destroy)
		
		self.leaf_search = Search(self.model)
		self.leaf_search.connect("activate", self._activate_object)
		self.leaf_search.connect("key-pressed", self._key_press)
		self.leaf_search.connect("cursor-changed", self._cursor_changed)
		
		self.action_search = Search(self.actions_model)
		self.action_search.connect("activate", self._activate_action)

		box = gtk.HBox()
		box.pack_start(self.leaf_search, True, True, 0)
		box.pack_start(self.action_search, True, True, 0)
		self.leaf_search.show()
		self.action_search.show()
		box.show()
		window.add(box)
		window.show()
		return window

	def source_rebase(self, src):
		self.source_stack = []
		self.push_source(src)
	
	def push_source(self, src):
		self.source = src
		self.source.set_refresh_callback(self.refresh_data)
		self.source_stack.insert(0, src)
	
	def pop_source(self):
		if len(self.source_stack) <= 1:
			raise
		else:
			self.source_stack.pop(0)
			self.source = self.source_stack[0]

	def refresh_data(self):
		self.kupfer = self.make_searchobj()
		self.match = None
		self.leaf_search.set_search_object(self.kupfer)	

	def make_searchobj(self):
		leaves = self.source.get_items() 
		return kupfer.Search(((leaf.value, leaf) for leaf in leaves))

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	def _cursor_changed(self, widget, leaf):
		actions = leaf.get_actions()
		sobj = kupfer.Search(((str(act), act) for act in actions))
		self.action_search.set_search_object(sobj)
	
	def _activate_action(self, widget, act):
		act.activate(self.leaf_search.get_current())
	
	def _key_press(self, widget, leaf, keyval):
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

	def _activate_object(self, widget, leaf):
		act = self.action_search.get_current()
		print act
		act.activate(leaf)

	def main(self):
		gtk.main()


if __name__ == '__main__':
	import sys
	from os import path

	import objects
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	dir = path.abspath(dir)
	dir_source = objects.DirectorySource(dir)
	file_source = objects.FileSource(sys.argv[1:], depth=2)
	source = objects.SourcesSource((dir_source, file_source))
	w = Browser(source)
	w.main()
