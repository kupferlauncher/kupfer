#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import itertools
import kupfer

class Model (object):
	def __init__(self):
		self.val_col = 0
		self.rank_col = 1
		self.obj_col = 2
		self.tree_model = gtk.ListStore(str, int, gobject.TYPE_PYOBJECT)

		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("item", cell)
		nbr_col = gtk.TreeViewColumn("rank", cell)

		col.add_attribute(cell, "text", 0)
		nbr_col.add_attribute(cell, "text", 1)
		self.columns = (col, nbr_col)
	
	def _get_column(self, treepath, col):
		iter = self.tree_model.get_iter(treepath)
		val = self.tree_model.get_value(iter, col)
		return val
	
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

	def append(self, value, rank, object):
		self.tree_model.append((value, rank, object))

	def clear(self):
		self.tree_model.clear()

class Browser (object):

	def __init__(self, datasource):
		"""
		"""
		self.model = Model()
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
		
		self.entry = gtk.Entry(max=0)
		self.entry.connect("changed", self._changed)
		self.entry.connect("activate", self._activate)

		self.label = gtk.Label("<match>")
		self.label.set_justify(gtk.JUSTIFY_LEFT)

		self.table = gtk.TreeView(self.model.tree_model)

		for col in self.model.columns:
			self.table.append_column(col)

		self.table.connect("row-activated", self._row_activated)
		self.table.connect("key-press-event", self._key_press)
		self.table.connect("cursor-changed", self._cursor_changed)

		self.actions_model = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
		self.actions_table = gtk.TreeView(self.actions_model)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Action", cell)
		col.add_attribute(cell, "text", 0)
		self.actions_table.append_column(col)

		self.actions_table.connect("row-activated", self._actions_row_activated)
		

		box = gtk.VBox()
		box.pack_start(self.entry, True, True, 0)
		box.pack_start(self.label, False, False, 0)
		box.pack_start(self.table, True, True, 0)
		box.pack_start(self.actions_table, True, True, 0)

		window.add(box)
		box.show()
		self.table.show()
		self.actions_table.show()
		self.entry.show()
		self.label.show()
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
			raise NoParent
		else:
			self.source_stack.pop(0)
			self.source = self.source_stack[0]

	def refresh_data(self):
		self.kupfer = self.make_searchobj()
		self.best_match = None
		self._reset()

	def make_searchobj(self):
		leaves = self.source.get_items() 
		return kupfer.Search(((leaf.value, leaf) for leaf in leaves))

	def _make_list(self):
		for leaf in itertools.islice(self.source.get_items(), 10):
			val, obj = leaf.value, leaf
			self.model.append(val, 0, obj)

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	def _reset(self):
		self.entry.grab_focus()
		self.entry.set_text("")
		self.label.set_text("")
		self.model.clear()
		self._make_list()

	def do_search(self, text):
		"""
		return the best item as (rank, name)
		"""
		# print "Type in search string"
		# in_str = raw_input()
		ranked_str = self.kupfer.search_objects(text)

		self.model.clear()
		for s in itertools.islice(ranked_str, 10):
			row = (s.value, s.rank, s.object)
			self.model.append(*row)
		top = ranked_str[0]
		# top.object is a leaf
		return (top.rank, top.object)
	
	def _changed(self, editable, data=None):
		text = editable.get_text()
		if not len(text):
			self.best_match = None
			return
		self.best_match = self.do_search(text)
		self.update_match()
	
	def _cursor_changed(self, treeview):
		path, col = treeview.get_cursor()
		if not path:
			return
		self.best_match = self.model.get_rank(path), self.model.get_object(path)
		self.update_match()
	
	def update_match(self):
		"""
		Update interface to display the currently selected match
		"""
		text = self.entry.get_text()
		rank, leaf = self.best_match
		res = ""
		idx = 0
		from xml.sax.saxutils import escape
		key = kupfer.remove_chars(text.lower(), " _-.")
		for n in leaf.value:
			if idx < len(key) and n.lower() == key[idx]:
				idx += 1
				res += ("<u>"+ escape(n) + "</u>")
			else:
				res += (escape(n))
		self.label.set_markup("%d: %s" % (rank, res))
		self.update_actions()
	
	def update_actions(self):
		rank, leaf = self.best_match
		self.actions_model.clear()
		actions = leaf.get_actions()
		if not len(actions):
			return
		for act in actions:
			self.actions_model.append((str(act), act))
	
	def _actions_row_activated(self, treeview, treepath, view_column, data=None):
		rank, leaf = self.best_match
		iter = self.actions_model.get_iter(treepath)
		action = self.actions_model.get_value(iter, 1)
		action.activate(leaf)


	def _row_activated(self, treeview, treepath, view_column, data=None):
		leaf = self.model.get_object(treepath)
		self._activate_object(leaf)
	
	def _key_press(self, widget, event, data=None):
		rightarrow = 0xFF53
		leftarrow = 0xFF51
		if event.keyval == rightarrow:
			treepath, col = self.table.get_cursor()
			if not treepath:
				return
			leaf = self.model.get_object(treepath)
			if not leaf.has_content():
				return
			self.push_source(leaf.content_source())
			
		elif event.keyval == leftarrow:
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
