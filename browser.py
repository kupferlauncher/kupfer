#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import gobject
import itertools
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

class Source (object):
	"""
	Source: Data provider for a kupfer browser

	required are
	set_refresh_callback
	get_items
	"""
	def set_refresh_callback(self, refresh_callback):
		"""
		Set function to be called on owner when data needs refresh
		"""
		self.refresh_callback = refresh_callback

	def get_items(self):
		"""
		return a list of leaves
		"""
		return []

	def __str__(self):
		return self.__class__.__name__

	def representation(self):
		"""
		Return represented object
		"""
		return self

class Leaf (object):
	def __init__(self, obj, value):
		self.object = obj
		self.value = value
	
	def __repr__(self):
		return "<%s %s at %x>" % (self.__class__.__name__, self.object, id(self))
	
	def has_content(self):
		return False
	
	def content_source(self):
		raise

	def get_actions(self):
		return ()

class FileLeaf (Leaf):
	def get_actions(self):
		return (Show(), Echo())

	def has_content(self):
		return path.isdir(self.object)

	def content_source(self):
		if self.has_content():
			return DirectorySource(self.object)
		else:
			return Leaf.content_source(self)

class Action (object):
	def activate(self, leaf):
		pass
	
	def activate_many(self, leaves):
		pass

class Show (Action):
	def activate(self, leaf):
		self._launch_file(leaf.object)

	def _launch_file(self, filepath):
		from gnomevfs import get_uri_from_local_path
		from gnome import url_show
		uri = get_uri_from_local_path(filepath)
		print filepath, uri
		try:
			url_show(uri)
		except Exception, info:
			print info

class Echo (Action):
	def activate(self, leaf):
		print "Echo:", leaf.object

class FileSource (Source):

	def __init__(self, dirlist, deep=False):
		self.dirlist = dirlist
		self.deep = deep

	def get_items(self):
		iters = []
		
		def mkgenerator(d, files):
			return (FileLeaf(f, path.basename(f)) for f in files)

		for d in self.dirlist:
			files = self._get_dirlist(d)
			iters.append(mkgenerator(d, files))
		return itertools.chain(*iters)

	def _exclude_file(self, filename):
		return filename.startswith(".") 

	def _get_dirlist(self, dir):
		def get_listing(dirlist, dirname, fnames):
			dirlist.extend([path.join(dirname, file) for file in fnames if not self._exclude_file(file)])

			if not self.deep:
			# don't recurse
				del fnames[:]

		dirlist = []
		path.walk(dir, get_listing, dirlist)
		return dirlist

class DirectorySource (FileSource):

	def __init__(self, dir):
		self.directory = dir
		self.deep = False

	def get_items(self):
		dirlist = self._get_dirlist(self.directory)
		items = (FileLeaf(file, path.basename(file)) for file in dirlist)
		return items

class SourcesSource (Source):

	def __init__(self, sources):
		self.sources = sources
	
	def get_items(self):
		return (Leaf(s, str(s)) for s in self.sources)


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
			obj = self.model.get_object(treepath)
			self.source.contains(obj)
			
		elif event.keyval == leftarrow:
			self.source.parent()

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
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	dir = path.abspath(dir)
	source = DirectorySource(dir)
	#source = FileSource(sys.argv[1:], deep=True)
	#source = SourcesSource((source,))
	w = Browser(source)
	w.main()

