#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import itertools
import kupfer

class ModelBase (object):
	def __init__(self, *columns):
		self.store = gtk.ListStore(*columns)

	def _get_column(self, treepath, col):
		iter = self.store.get_iter(treepath)
		val = self.store.get_value(iter, col)
		return val

	def append(self, row):
		self.store.append(row)

	def clear(self):
		self.store.clear()

class LeafModel (ModelBase):
	def __init__(self):
		ModelBase.__init__(self, str, int, gobject.TYPE_PYOBJECT)
		self.val_col = 0
		self.rank_col = 1
		self.obj_col = 2

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("item", cell)
		nbr_col = gtk.TreeViewColumn("rank", cell)

		col.add_attribute(cell, "text", 0)
		nbr_col.add_attribute(cell, "text", 1)
		self.columns = (col, nbr_col)
	
	def get_value(self, treepath):
		"""
		Return model's value for treeview's path
		"""
		return self._get_column(treepath, self.val_col)

	def get_object(self, treepath):
		"""
		Return model's object for the treeview path
		"""
		return self._get_column(treepath, self.obj_col)

	def get_rank(self, treepath):
		"""
		Return model's rank for the treeview path
		"""
		return self._get_column(treepath, self.rank_col)

class ActionModel (ModelBase):
	def __init__(self):
		ModelBase.__init__(self, str, gtk.gdk.Pixbuf, gobject.TYPE_PYOBJECT)
		self.name_col, self.icon_col, self.obj_col = 0,1,2
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Action", cell)
		col.add_attribute(cell, "text", self.name_col)
		cell = gtk.CellRendererPixbuf()
		col2 = gtk.TreeViewColumn("", cell)
		col2.add_attribute(cell, "pixbuf", self.icon_col)
		self.columns = (col, col2)
	
	def get_name(self, path):
		return self._get_column(path, self.name_col)
	
	def get_action(self, path):
		return self._get_column(path, self.obj_col)


class Search (gtk.Bin):
	__gtype_name__ = 'Searcher'
	def __init__(self, model):
		gobject.GObject.__init__(self)
		self.model = model
		self.search_object = None
		self.callbacks = {}

		self.entry = gtk.Entry(max=0)
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate)

		self.label = gtk.Label("<match>")
		self.label.set_justify(gtk.JUSTIFY_LEFT)
		self.icon_view = gtk.Image()

		self.table = gtk.TreeView(self.model.store)

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
		box.pack_start(self.entry, False, False, 0)
		box.pack_start(infobox, False, False, 0)
		box.pack_start(self.table, True, True, 0)
		self.add(box)
		box.show_all()
		#self.set_property("child", box)
		self.__child = box
	
	def set_callback(self, name, func):
		self.callbacks[name] = func

	def do_size_request (self, requisition):
		requisition.width, requisition.height = self.__child.size_request ()

	def do_size_allocate (self, allocation):
		self.__child.size_allocate (allocation)

	def do_forall (self, include_internals, callback, user_data):
		callback (self.__child, user_data)

	def _get_cur_object(self):
		path, col = self.table.get_cursor()
		if not path:
			return None
		return self.model.get_object(path)

	def _activate(self, entry):
		if "activate" not in self.callbacks:
			return
		rank, obj = self.best_match
		self.callbacks["activate"](obj)
	
	def _row_activated(self, treeview, path, col):
		if "activate" not in self.callbacks:
			return
		obj = self._get_cur_object()
		self.callbacks["activate"](obj)

	def _key_press(self, treeview, event):
		if "key_press" not in self.callbacks:
			return
		obj = self._get_cur_object()
		self.callbacks["key_press"](obj, event.keyval)
	
	def _cursor_changed(self, treeview):
		path, col = treeview.get_cursor()
		if not path:
			return
		self.best_match = self.model.get_rank(path), self.model.get_object(path)
		self.update_match()

	def reset(self):
		self.entry.grab_focus()
		self.entry.set_text("")
		self.label.set_text("")
		self.model.clear()

	def do_search(self, text):
		"""
		return the best item as (rank, name)
		"""
		# print "Type in search string"
		# in_str = raw_input()
		ranked_str = self.search_object.search_objects(text)

		self.model.clear()
		for s in itertools.islice(ranked_str, 10):
			row = (s.value, s.rank, s.object)
			self.model.append(row)
		top = ranked_str[0]
		# top.object is a leaf
		return (top.rank, top.object)
	
	def _changed(self, editable):
		text = editable.get_text()
		if not len(text):
			self.best_match = None
			return
		self.best_match = self.do_search(text)
		self.update_match()
	
	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		text = self.entry.get_text()
		rank, leaf = self.best_match
		print "Marking", leaf
		# update icon
		icon = leaf.get_pixbuf()
		if icon:
			self.icon_view.set_from_pixbuf(icon)
		else:
			self.icon_view.clear()

		#update text label
		markup = ""
		idx = 0
		from xml.sax.saxutils import escape
		key = kupfer.remove_chars(text.lower(), " _-.")
		for n in leaf.value:
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
		self.leaf_search.set_callback("activate", self._activate_object)
		self.leaf_search.set_callback("key_press", self._key_press)
		window.add(self.leaf_search)
		window.show_all()
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
			raise NoParent
		else:
			self.source_stack.pop(0)
			self.source = self.source_stack[0]

	def refresh_data(self):
		self.kupfer = self.make_searchobj()
		self.best_match = None
		self.leaf_search.set_search_object(self.kupfer)	

	def make_searchobj(self):
		leaves = self.source.get_items() 
		return kupfer.Search(((leaf.value, leaf) for leaf in leaves))

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	
	def update_actions(self):
		rank, leaf = self.best_match
		self.actions_model.clear()
		actions = leaf.get_actions()
		if not len(actions):
			return
		for act in actions:
			self.actions_model.append((str(act), act.get_pixbuf(), act))
	
	def _actions_row_activated(self, treeview, treepath, view_column, data=None):
		rank, leaf = self.best_match
		iter = self.actions_model.get_iter(treepath)
		action = self.actions_model.get_value(iter, 2)
		action.activate(leaf)


	def _row_activated(self, treeview, treepath, view_column, data=None):
		leaf = self.model.get_object(treepath)
		self._activate_object(leaf)
	
	def _key_press(self, leaf, keyval):
		rightarrow = 0xFF53
		leftarrow = 0xFF51
		if keyval == rightarrow:
			if not leaf.has_content():
				return
			self.push_source(leaf.content_source())
			
		elif keyval == leftarrow:
			try:
				self.pop_source()
			except NoParent:
				if self.source.has_parent():
					self.source_rebase(self.source.get_parent())
		else:
			return
		self.refresh_data()

	def _activate(self, entry, data=None):
		"""
		Text input was activated (enter key)
		"""
		if not self.best_match:
			return
		rank, leaf= self.best_match
		self._activate_object(leaf)
	
	def _activate_object(self, leaf):
		acts = leaf.get_actions()
		print "Leaf", leaf, "has actions", acts
		if len(acts):
			act = acts[0]
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
