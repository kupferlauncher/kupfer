#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import kupfer

from os import path

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

	def append(self, value, rank, object):
		self.tree_model.append((value, rank, object))

	def clear(self):
		self.tree_model.clear()

class DataSource (object):
	"""
	abstract superclass
	"""
	def set_refresh_callback(self, refresh_callback):
		"""
		Set function to be called on owner when data needs refresh
		"""
		self.refresh_callback = refresh_callback

	def get_items(self):
		"""
		return a list of (value, object) tuples,
		where value is a rank-based string
		"""
		return []

	def activate(self, object):
		"""
		Callback when object is activated
		"""
		pass
	
	def contains(self, object):
		"""
		Called when object is entered
		"""
		pass
	
	def parent(self):
		"""
		called when the current context is left
		"""
		pass

class DirectorySource (DataSource):

	def __init__(self, dir):
		self.directory = dir

	def get_items(self):
		dirlist = self._get_dirlist(self.directory)
		items = ((file, path.join(self.directory, file)) for file in dirlist)
		return items

	def _get_dirlist(self, dir):
		def get_listing(dirlist, dirname, fnames):
			dirlist.extend([file for file in fnames if not file.startswith(".")])
			# don't recurse
			del fnames[:]

		dirlist = []
		path.walk(dir, get_listing, dirlist)
		return dirlist

	def activate(self, obj):
		self._launch_file(obj)

	def _launch_file(self, filepath):
		from gnomevfs import get_uri_from_local_path
		from gnome import url_show
		uri = get_uri_from_local_path(filepath)
		print filepath, uri
		try:
			url_show(uri)
		except Exception, info:
			print info
	
	def parent(self):
		self.directory = path.normpath(path.join(self.directory, path.pardir))
		print self.directory
		self.refresh_callback()

class Browser (object):

	def __init__(self, datasource):
		"""
		"""
		self.model = Model()
		self.datasource = datasource
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

		self.label = gtk.Label("<file>")
		self.label.set_justify(gtk.JUSTIFY_LEFT)

		self.table = gtk.TreeView(self.model.tree_model)

		for col in self.model.columns:
			self.table.append_column(col)

		self.table.connect("row-activated", self._row_activated)
		self.table.connect("key-press-event", self._key_press)

		box = gtk.VBox()
		box.pack_start(self.entry, True, True, 0)
		box.pack_start(self.label, False, False, 0)
		box.pack_start(self.table, True, True, 0)

		window.add(box)
		box.show()
		self.table.show()
		self.entry.show()
		self.label.show()
		window.show()
		return window

	def refresh_data(self):
		self.kupfer = self.make_searchobj()
		self.best_match = None
		self._reset()

	def make_searchobj(self):
		return kupfer.Search(self.datasource.get_items()) 

	def _make_list(self):
		for i, item in enumerate(self.datasource.get_items()):
			if i > 10:
				break
			val, obj = item
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
		for idx, s in enumerate(ranked_str):
			print s
			row = (s.value, s.rank, s.object)
			self.model.append(*row)
			if idx > 10:
				break
		print "---"
		top = ranked_str[0]
		return (top.value, top.rank, top.object)
	
	def _changed(self, editable, data=None):
		text = editable.get_text()
		if not len(text):
			self.best_match = None
			return
		self.best_match = self.do_search(text)
		name, rank, obj = self.best_match

		res = ""
		idx = 0
		from xml.sax.saxutils import escape
		key = kupfer.remove_chars(text.lower(), " _-.")
		for n in name:
			if idx < len(key) and n.lower() == key[idx]:
				idx += 1
				res += ("<u>"+ escape(n) + "</u>")
			else:
				res += (escape(n))
		self.label.set_markup("%d: %s" % (rank, res))
	
	def _row_activated(self, treeview, treepath, view_column, data=None):
		obj = self.model.get_object(treepath)
		self._activate_object(obj)
	
	def _key_press(self, widget, event, data=None):
		rightarrow = 0xFF53
		leftarrow = 0xFF51
		dirpath = None
		if event.keyval == rightarrow:
			treepath, col = self.table.get_cursor()
			if not treepath:
				return
			obj = self.model.get_object(treepath)
			self.datasource.contains(obj)
			
		elif event.keyval == leftarrow:
			self.datasource.parent()

	def _activate(self, entry, data=None):
		"""
		Text input was activated (enter key)
		"""
		if not self.best_match:
			return
		name, rank, object= self.best_match
		self._activate_object(object)
	
	def _activate_object(self, obj):
		self.datasource.activate(obj)

	def main(self):
		gtk.main()

if __name__ == '__main__':
	import sys
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	dir = path.abspath(dir)
	source = DirectorySource(dir)
	w = Browser(source)
	source.set_refresh_callback(w.refresh_data)
	w.main()

