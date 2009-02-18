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
			#rankable._words = tuple(split_at(value, self.wordsep))
			#rankable._abbrev = "".join(w[:1].lower() for w in rankable._words)
			all.append(rankable)
		return all

	def rank_objects(self, objects, key):
		"""
		objects --
		key -- 
		"""
		from relevance import score
		for obj in objects:
			obj.rank = score(obj.value, key)*100

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

		self.old_key = key
		self.old_list = search_base

		# do the searching
		self.rank_objects(search_base, key)
		search_base.sort(key=lambda item: (-item.rank, item.value), reverse=False)
		return search_base
	
