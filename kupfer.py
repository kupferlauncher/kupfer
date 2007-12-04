# -*- coding: UTF-8 -*-

def split_at(s, seps):
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

def upper_str(s):
	return "".join([c for c in s if c.isupper()])

def remove_chars(s, clist):
	"""
	remove any char in string clist from s and return the result
	"""
	return "".join([c for c in s if c not in clist])

def remove_chars_unicode(s, clist):
	"""
	remove any char in string clist from s and return the result
	"""
	return u"".join([c for c in s if c not in clist])

class Rankable (object):
	"""
	Rankable has an object (represented item),
	value (determines rank) and an associated rank
	"""
	def __init__(self, value, object=None):
		self.rank = 0
		self.value = value
		self.object = object
	
	def __str__(self):
		return "%s: %s" % (self.rank, self.value)

	def __repr__(self):
		return "<Rankable %s repres %s at %x>" % (str(self), repr(self.object), id(self))

class Search (object):
	"""
	Initialize the search object with a list of
	(value, object) tuples that are to be ranked.
	Returns a sorted list of Rankable instances
	"""
	
	def __init__(self, items):
		"""
		items: sequence of (value, object) tuples
		"""
		self.wordsep = " .-_"
		self.ignorechars = "()[]"
		self.search_base = []
		
		for val, obj in items:
			self.search_base.append(Rankable(val, obj))
		self.preprocess_objects(self.search_base)

	def preprocess_objects(self, objects):
		"""
		process the list of objects, store
		ranking metadata in them
		"""
		for item in objects:
			item.value = remove_chars(item.value, self.ignorechars)
			item._words = split_at(item.value, self.wordsep)
			item._abbrev = self.abbrev_str(item._words)

	def abbrev_str(self, words):
		first_chars = "".join([w[0] for w in words if len(w)])
		return first_chars.lower()

	def rank_string(self, s, key):
		# match values
		exact_v = 20
		start_v = 10
		substr_v = 5

		rank = 0
		if s == key:
			rank += exact_v
		elif s.startswith(key):
			rank += start_v
		elif key in s:
			rank += substr_v
		else:
			rank += self.common_prefix(s, key)
		return rank
	
	def rank_words(self, item, key):
		# match weights
		word_w = 2
		rank = 0
		if key in item._words:
			# exact subword match
			rank += word_w*len(key)
		else:
			# score prefixes of subwords
			# example:
			# key: contdesk
			# matches configure-the-thing.desktop as 3-1-0-4 for a score of 7
			# key: conddesk matches only 3-0-0-1
			idx = 0
			word_pfx = 0
			for w in item._words:
				pfx = self.common_prefix(w, key[idx:])
				idx += pfx
				word_pfx += pfx
			rank += word_pfx

		if rank > 5: print item.value, "words", rank
		return rank

	def common_letters(self, s, key, lower=False):
		"""
		count number of common letters
		(in order)

		if lower is True, will lowercase
		"""
		if lower:
			s = s.lower()
			key = key.lower()
		idx = 0
		for c in s:
			if c == key[idx]:
				idx += 1
				if idx == len(key):
					break
		return idx

	def common_prefix(self, s, key):
		"""
		count nbr of common letters in common prefix
		"""
		common = 0
		for c1, c2 in zip(s, key):
			if c1 == c2:
				common += 1
			else:
				break
		return common

	def rank_objects(self, objects, key):
		"""
		objects --
		key -- 
		"""
		normal_w = 10
		abbrev_w = 7 
		words_w = 10
		common_letter_w = 3
		part_w = 1

		lower_key = key.lower()

		def rank_key(val, abbrev, key):
			rank = 0
			rank += normal_w * self.rank_string(val, key)
			rank += abbrev_w * self.rank_string(abbrev, key)
			rank += common_letter_w * self.common_letters(val, key)
			rank += common_letter_w * self.common_letters(abbrev, key)
			return rank

		for item in objects:
			val = item.value.lower()
			abbrev = item._abbrev
			rank = 0
			rank += normal_w * rank_key(val, abbrev, lower_key)
			rank += normal_w * words_w * self.rank_words(item, lower_key)
			# do parts
			keyparts = split_at(lower_key, self.wordsep)
			if len(keyparts) > 1:
				for part in keyparts:
					if not len(part):
						continue
					rank += part_w * rank_key(val, abbrev, part)
					rank += part_w * words_w * self.rank_words(item, part)
			item.rank = rank

	def search_objects(self, key):
		"""
		key -- string key
		"""
		# only sort on worthwhile objects
		for item in self.search_base:
			item.rank = self.common_letters(item.value, key, lower=True)
		objects = (item for item in self.search_base if item.rank)

		self.rank_objects(objects, key)
		self.search_base.sort(key=lambda item: item.rank, reverse=True)
		return self.search_base
	
