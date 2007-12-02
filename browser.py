#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import gtk
import kupfer

from os import path

class Model (object):
	def __init__(self):
		self.tree_model = gtk.ListStore(str, int)

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
		iter = self.tree_model.get_iter(treepath)
		val = self.tree_model.get_value(iter, 0)
		return val

class Window (object):

	def __init__(self, dir):
		"""
		"""
		self.directory = dir
		self.model = Model()
		self.window = self._setup_window()
		self.kupfer = self.make_searchobj(dir) 
		self.best_match = None
		self._reset()
	
	def make_searchobj(self, dir):
		dirlist = self._get_dirlist(dir)
		return kupfer.Search(dirlist)
	
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

	def _get_dirlist(self, dir="."):
		
		def get_listing(dirlist, dirname, fnames):
			dirlist.extend([file for file in fnames if not file.startswith(".")])
			# don't recurse
			del fnames[:]

		dirlist = []
		path.walk(dir, get_listing, dirlist)
		return dirlist

	def _make_filelist(self):
		list = self._get_dirlist(self.directory)

		sort_key = (lambda file: (path.isdir(file), file))
		list.sort(key=sort_key)
		for i, file in enumerate(list):
			if i > 10:
				break
			self.model.tree_model.append((file, 0))

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	def _reset(self):
		self.entry.grab_focus()
		self.entry.set_text("")
		self.label.set_text("in %s" % self.directory)
		self.model.tree_model.clear()
		self._make_filelist()

	def do_search(self, text):
		"""
		return the best item as (rank, name)
		"""
		# print "Type in search string"
		# in_str = raw_input()
		ranked_str = self.kupfer.search_objects(text)

		self.model.tree_model.clear()
		for idx, s in enumerate(ranked_str):
			print s
			row = (s.value, s.rank)
			self.model.tree_model.append(row)
			if idx > 10:
				break
		print "---"
		top = ranked_str[0]
		return (top.value, top.rank)
	
	def _changed(self, editable, data=None):
		text = editable.get_text()
		if not len(text):
			self.best_match = None
			return
		name, rank = self.do_search(text)
		self.best_match = rank, name
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
		#self.label.set_text("%d: %s" % self.best_match)
		self.label.set_markup("%d: %s" % (rank, res))
	
	def _row_activated(self, treeview, treepath, view_column, data=None):
		val = self.model.get_value(treepath)
		self._launch_name(val)
	
	def _key_press(self, widget, event, data=None):
		rightarrow = 0xFF53
		leftarrow = 0xFF51
		dirpath = None
		if event.keyval == rightarrow:
			treepath, col = self.table.get_cursor()
			if not treepath:
				return
			val = self.model.get_value(treepath)
			dirpath = path.join(self.directory, val) 
			if not path.isdir(dirpath):
				dirpath = None
			
		elif event.keyval == leftarrow:
			dirpath = path.normpath(path.join(self.directory, ".."))
			
		if dirpath:
			self.directory = dirpath
			self.kupfer = self.make_searchobj(dirpath)
			self._reset()

	def _activate(self, entry, data=None):
		"""
		Text input was activated (enter key)
		"""
		if not self.best_match:
			return
		rank, name = self.best_match

		self._launch_name(name)

	def _launch_name(self, name):
		from gnomevfs import get_uri_from_local_path
		from gnome import url_show
		file = path.join(self.directory, name) 
		uri = get_uri_from_local_path(file)
		print file, uri
		try:
			url_show(uri)
		except Exception, info:
			print info

	def main(self):
		gtk.main()

if __name__ == '__main__':
	import sys
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	dir = path.abspath(dir)
	w = Window(dir)
	w.main()

