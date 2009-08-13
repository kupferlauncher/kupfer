# -*- coding: UTF-8 -*-

import locale

from kupfer import learn
from kupfer.relevance import score

def make_rankables(itr, rank=0):
	return (Rankable(unicode(obj), obj, rank) for obj in itr)

def make_alpharankables(itr, rank=0):
	"""make rankables that sort alphabetically"""
	return (AlphaRankable(unicode(obj), obj, rank) for obj in itr)
def make_nosortrankables(itr, rank=0):
	"""make rankables that do not sort """
	return (NoSortRankable(unicode(obj), obj, rank) for obj in itr)

class Rankable (object):
	"""
	Rankable has an object (represented item),
	value (determines rank) and an associated rank
	"""
	# To save memory with (really) many Rankables
	__slots__ = ("rank", "value", "object", "aliases")
	def __init__(self, value, obj, rank=0):
		self.rank = rank
		self.value = value
		self.object = obj
		self.aliases = getattr(obj, "name_aliases", ())
	
	def __hash__(self):
		return hash(self.value)

	def __eq__(self, other):
		return (self.object == self.object)

	def __cmp__(self, other):
		if isinstance(other, Rankable):
			p1 = -cmp(self.rank, other.rank)
			p2 = 0
			if p1 == 0 and self.rank:
				p2 = locale.strcoll(self.value, other.value)
			return p1 + p2
		return -1
	
	def __str__(self):
		return "%s: %s" % (self.rank, self.value)

	def __repr__(self):
		return "<Rankable %s repres %s at %x>" % (str(self), repr(self.object), id(self))

class AlphaRankable (Rankable):
	"""Like rankable but sorts alphabetically"""
	def __cmp__(self, other):
		if isinstance(other, Rankable):
			return locale.strcoll(self.value, other.value)
		return -1
class NoSortRankable (Rankable):
	"""Like rankable but all items equal"""
	def __cmp__(self, other):
		if isinstance(other, Rankable):
			return 0
		return -1

def bonus_objects(rankables, key):
	"""generator of @rankables that have mnemonics for @key

	rank is added to prev rank, all items are yielded"""
	key = key.lower()
	get_record_score = learn.get_record_score
	for obj in rankables:
		obj.rank += get_record_score(obj.object, key)
		obj.rank += obj.object.rank_adjust
		yield obj

def add_rank_objects(rankables, rank):
	for obj in rankables:
		obj.rank += rank
		yield obj

def score_objects(rankables, key):
	"""Return @rankables that pass with a >0 rank for @key,

	rank is added to previous rank,
	if not @key, then all items are returned"""
	key = key.lower()
	for rb in rankables:
		# Rank object
		rank = score(rb.value, key)*100
		maxval = None
		for alias in rb.aliases:
			# consider aliases and change rb.value if alias is better
			# aliases rank lower so that value is chosen when close
			arank = score(alias, key)*95
			if arank > rank:
				rank = arank
				rb.value = alias
		rb.rank = rank
		if rb.rank:
			yield rb

