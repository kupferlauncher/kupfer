#!/usr/bin/python

import gtk

class KupferSearch (object):
	"""
	Loads a list of strings and performs a smart search,
	returning a ranked list
	"""
	
	def __init__(self, search_base, wordsep=" .-_"):
		self.wordsep = wordsep
		self.search_base = search_base

	def rank_string(self, s, key):
		# match values
		exact_v = 20
		start_v = 10
		wordm_v = 8
		substr_v = 5

		s = s.lower()
		key = key.lower()
		rank = 0
		if s == key:
			rank += exact_v
		elif s.startswith(key):
			rank += start_v
		elif key in s:
			rank += substr_v
		if key in self.split_at(s, self.wordsep):
			# exact subword match
			rank += wordm_v
		return rank

	def split_at(self, s, seps):
		"""
		Split at string at any char in seps
		"""
		parts = []
		last = 0
		for i, c in enumerate(s):
			if c in seps:
				parts.append(s[last:i])
				last = i+1
		if last == 0:
			parts.append(s)
		else:
			parts.append(s[last:])
		return parts

	def common_letters(self, s, key, case_insensitive=True):
		"""
		count number of common letters
		(in order)
		"""
		if case_insensitive:
			s = s.lower()
			key = key.lower()
		idx = 0
		for c in s:
			if c == key[idx]:
				idx += 1
				if idx == len(key):
					break
		return idx

	def abbrev_str(self, s):
		words = self.split_at(s, self.wordsep)
		first_chars = "".join([w[0] for w in words if len(w)])
		return first_chars

	def upper_str(self, s):
		return "".join([c for c in s if c.isupper()])

	def rank_objects(self, objects, key):
		"""
		objects --
		key -- 
		"""
		normal_w = 10
		abbrev_w = 7 
		common_letter_w = 3
		part_w = 1
		rank_list = []

		def rank_key(obj, key):
			rank = 0
			rank += normal_w * self.rank_string(i, key)
			abbrev = self.abbrev_str(i)
			rank += abbrev_w * self.rank_string(abbrev, key)
			rank += common_letter_w * self.common_letters(i, key)
			rank += common_letter_w * self.common_letters(abbrev, key)

			return rank

		for i in objects:
			rank = 0
			rank += normal_w * rank_key(i, key)
			# do parts
			keyparts = key.split()
			for part in keyparts:
				rank += part_w * rank_key(i, part)
			
			rank_list.append((rank,i))
		rank_list.sort(key= lambda item: item[0], reverse=True)
		return rank_list

	def search_objects(self, key):
		"""
		key -- string key
		"""
		ranked_str = self.rank_objects(self.search_base, key)
		return ranked_str

class KupferWindow (object):

	def __init__(self, dir):
		"""
		"""
		self.directory = dir
		self.window = self._setup_window()
		dirlist = self._get_dirlist(dir)
		self.kupfer = KupferSearch(dirlist)
		self.best_match = None
	
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

		box = gtk.VBox()
		box.pack_start(self.entry, True, True, 0)
		box.pack_start(self.label, False, False, 0)

		window.add(box)
		box.show()
		self.entry.show()
		self.label.show()
		window.show()
		return window

	def _get_dirlist(self, dir="."):
		
		from os import path
		
		def get_listing(dirlist, dirname, fnames):
			dirlist.extend(fnames)
			# don't recurse
			del fnames[:]

		dirlist = []
		path.walk(dir, get_listing, dirlist)
		return dirlist

	def _destroy(self, widget, data=None):
		gtk.main_quit()

	def do_search(self, text):
		"""
		return the best item as (rank, name)
		"""
		# print "Type in search string"
		# in_str = raw_input()
		ranked_str = self.kupfer.search_objects(text)

		for idx, s in enumerate(ranked_str):
			print s
			if idx > 10:
				break
		print "---"
		return ranked_str[0]
	
	def _changed(self, editable, data=None):
		text = editable.get_text()
		if not len(text):
			self.best_match = None
			return
		rank, name = self.do_search(text)
		self.best_match = rank, name
		res = ""
		idx = 0
		from xml.sax.saxutils import escape
		key = text.lower()
		for n in name:
			if idx < len(text) and n.lower() == text[idx]:
				idx += 1
				res += ("<u>"+ escape(n) + "</u>")
			else:
				res += (escape(n))
		#self.label.set_text("%d: %s" % self.best_match)
		self.label.set_markup("%d: %s" % (rank, res))
	
	def _activate(self, entry, data=None):
		"""
		Text input was activated (enter key)
		"""
		if not self.best_match:
			return
		from os import path, system
		rank, name = self.best_match
		file = path.join(self.directory, name) 
		print file

		system("%s '%s'" % ("gnome-open", file))

	def main(self):
		gtk.main()

if __name__ == '__main__':
	import sys
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	w = KupferWindow(dir)
	w.main()
	
