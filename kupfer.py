# -*- coding: UTF-8 -*-

def split_at(s, seps):
	"""
	Split string at any char in seps (generator)
	"""
	last = 0
	for i, c in enumerate(s):
		if c in seps:
			yield s[last:i]
			last = i+1
	if last == 0:
		yield s
	else:
		yield s[last:]

class Rankable (object):
	"""
	Rankable has an object (represented item),
	value (determines rank) and an associated rank
	"""
	# To save memory with (really) many Rankables
	__slots__ = ("rank", "value", "object", "_words", "_abbrev")
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
		self.wordsep = " .-_/"
		self.ignorechars = "()[]"
		self.search_base = []
		self.old_key = None
		self.old_list = None
		
		self.search_base = self.create_rankables(items)

	def create_rankables(self, items):
		"""
		massage the list of items, store value, object and
		ranking metadata in them
		"""
		all = []
		for val, obj in items:
			value = "".join(c for c in val if c not in self.ignorechars)

			rankable = Rankable(value, obj)
			rankable._words = tuple(split_at(value, self.wordsep))
			rankable._abbrev = "".join(w[:1].lower() for w in rankable._words)
			all.append(rankable)
		return all

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
			if idx == len(key):
				break
			if c == key[idx]:
				idx += 1
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
		abbrev_w = 5
		words_w = 10
		common_letter_w = 3
		all_common_w = 9
		part_w = 1

		lower_key = key.lower()

		def rank_key(val, abbrev, key):
			rank = 0
			rank += normal_w * self.rank_string(val, key)
			rank += abbrev_w * self.rank_string(abbrev, key)

			com_let = self.common_letters(val, key)
			if com_let == len(key): rank += all_common_w * com_let
			else: rank += common_letter_w * com_let
			rank += common_letter_w * self.common_letters(abbrev, key)
			return rank

		for item in objects:
			val = item.value.lower()
			abbrev = item._abbrev
			rank = 0
			rank += normal_w * rank_key(val, abbrev, lower_key)
			rank += normal_w * words_w * self.rank_words(item, lower_key)
			# do parts
			keyparts = tuple(split_at(lower_key, self.wordsep))
			if len(keyparts) > 1:
				for part in keyparts:
					if not part:
						continue
					rank += part_w * rank_key(val, abbrev, part)
					rank += part_w * words_w * self.rank_words(item, part)
			item.rank = rank

	def search_objects(self, key):
		"""
		key -- string key

		Search all loaded objects with the given key,
		and return all objects (as Rankables) with non-null rank
		"""
		if not self.old_key or not key.startswith(self.old_key):
			search_base = self.search_base
			self.old_list = None
		else:
			search_base = self.old_list
		# only sort on worthwhile objects
		# only filter on first word to make it simple
		for key_part in split_at(key, self.wordsep):
			if key_part:
				break
		else:
			key_part = key
		part_len = len(key_part)
		for item in search_base:
			# item has to contain all of key, in the right order
			com = self.common_letters(item.value, key_part, lower=True)
			item.rank = (part_len == com)

		objects = [item for item in search_base if item.rank]

		self.old_key = key
		self.old_list = objects

		# do the searching
		self.rank_objects(objects, key)
		objects.sort(key=lambda item: (-item.rank, item.value), reverse=False)
		return objects
	
