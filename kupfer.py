#!/usr/bin/python

class KupferSearch (object):
	
	def __init__(self, search_base, wordsep=" .-_"):
		self.wordsep = wordsep
		self.search_base = search_base

	def rank_string(self, s, key):
		s = s.lower()
		key = key.lower()
		rank = 0
		if s.startswith(key):
			rank+=10
		elif key in s:
			rank+=5
		if key in self.split_at(s, self.wordsep):
			# exact word match
			rank+=8
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
			rank += normal_w* self.rank_string(i, key)
			abbrev = self.abbrev_str(i)
			rank += abbrev_w * self.rank_string(abbrev, key)
			rank += common_letter_w * self.common_letters(i, key)

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

import gtk 
class WindowControl (object):

	def __init__(self, change_callback, change_context):
		"""
		change_callback: callback for changed entry text
			def change_callback(text, context)
		"""
		self.change_callback = change_callback
		self.change_context = change_context

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("destroy", self._destroy)
		
		self.entry = gtk.Entry(max=0)
		self.entry.connect("changed", self._changed)

		self.window.add(self.entry)
		self.entry.show()
		self.window.show()
	
	def _destroy(self, widget, data=None):
		gtk.main_quit()
	
	def _changed(self, editable, data=None):
		text = editable.get_text()
		print "changed val to", text 
		if self.change_callback:
			self.change_callback(text, self.change_context)

	def main(self):
		gtk.main()

if __name__ == '__main__':
	
	from os import path
	
	def get_listing(dirlist, dirname, fnames):
		dirlist.extend(fnames)
		# don't recurse
		del fnames[:]

	dirlist = []
	# get items in curdir
	path.walk("/home/ulrik/Desktop", get_listing, dirlist)

	kupfer = KupferSearch(dirlist)

	def do_search(text, context=None):
		# print "Type in search string"
		# in_str = raw_input()
		if not len(text):
			return
		ranked_str = kupfer.search_objects(text)

		for idx, s in enumerate(ranked_str):
			print s
			if idx > 10:
				break
		print "---"

	w = WindowControl(do_search, None)
	w.main()
	
