# -*- coding: UTF-8 -*-

import learn
from relevance import score

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

def make_rankables(itr, rank=0):
	return (Rankable(unicode(obj), obj, rank) for obj in itr)

class Rankable (object):
	"""
	Rankable has an object (represented item),
	value (determines rank) and an associated rank
	"""
	# To save memory with (really) many Rankables
	__slots__ = ("rank", "value", "object")
	def __init__(self, value, object=None, rank=0):
		self.rank = rank
		self.value = value
		self.object = object
	
	def __hash__(self):
		return hash(self.value)

	def __eq__(self, other):
		return (self.object == self.object)

	def _key(self):
		return (-item.rank, item.rank and item.value)

	def __cmp__(self, other):
		if isinstance(other, Rankable):
			return cmp(self._key, other._key)
		return -1
	
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
		self.old_key = None
		self.old_list = None
		
		self.search_base = [Rankable(val,obj) for val, obj in items]

	def rank_objects(self, objects, key):
		"""
		Assign score to all objects and yield the
		ones that have nonzero
		"""
		from relevance import score

		# If there is no search @key,
		# simply list objects by recorded score
		if key:
			for obj in objects:
				# Rank object
				# And if matches, add recorded score as well
				obj.rank = score(obj.value, key)*100
				if obj.rank:
					obj.rank += learn.get_record_score(obj.value, key)
					yield obj
		else:
			for obj in objects:
				obj.rank = learn.get_record_score(obj.value, key)
				yield obj
	
	def search_objects(self, key):
		"""
		key -- string key

		Search all loaded objects with the given key,
		and return all objects (as Rankables) with non-null rank
		"""
		key = key.lower()
		if not self.old_key or not key.startswith(self.old_key):
			search_base = self.search_base
			self.old_list = None
		else:
			search_base = self.old_list

		# do the searching
		self.old_key = key
		def itemranker(item):
			"""
			Sort key for the items.
			Sort first by rank, then by value (name)
			(but only sort by value if rank >= 0 to keep
			default ordering!)
			"""
			return (-item.rank, item.rank and item.value)

		self.old_list = list(sorted(self.rank_objects(search_base, key), key=itemranker))
		return self.old_list
	
def bonus_objects(rankables, key):
	"""generator of @rankables that have mnemonics for @key

	rank is added to prev rank, all items are yielded"""
	get_record_score = learn.get_record_score
	for obj in rankables:
		obj.rank += get_record_score(obj.value, key)
		yield obj

def add_rank_objects(rankables, rank):
	for obj in rankables:
		obj.rank += rank
		yield obj

def score_objects(rankables, key):
	"""Generator of @rankables that pass with a >0 rank for @key,

	rank is added to previous rank"""
	if not key:
		return
	for obj in rankables:
		# Rank object
		# And if matches, add recorded score as well
		obj.rank += score(obj.value, key)*100
		if obj.rank:
			yield obj

