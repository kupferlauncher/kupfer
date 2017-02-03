import itertools

try:
	from collections import OrderedDict
except ImportError:
	from UserDict import DictMixin
	OrderedDict = None

class SavedIterable (object):
	"""Wrap an iterable and cache it.

	The SavedIterable can be accessed streamingly, while still being
	incrementally cached. Later attempts to iterate it will access the
	whole of the sequence.

	When it has been cached to its full extent once, it reduces to a
	thin wrapper of a sequence iterator. The SavedIterable will pickle
	into a list.

	>>> s = SavedIterable(xrange(5))
	>>> iter(s).next()
	0
	>>> list(s)
	[0, 1, 2, 3, 4]

	>>> iter(s)   # doctest: +ELLIPSIS
	<listiterator object at 0x...>

	>>> import pickle
	>>> pickle.loads(pickle.dumps(s))
	[0, 1, 2, 3, 4]

	>>> u = SavedIterable(xrange(5))
	>>> one, two = iter(u), iter(u)
	>>> one.next(), two.next()
	(0, 0)
	>>> list(two)
	[1, 2, 3, 4]
	>>> list(one)
	[1, 2, 3, 4]

	>>> SavedIterable(range(3))
	[0, 1, 2]
	"""
	def __new__(cls, iterable):
		if isinstance(iterable, list):
			return iterable
		return object.__new__(cls)
	def __init__(self, iterable):
		self.iterator = iter(iterable)
		self.data = []
	def __iter__(self):
		if self.iterator is None:
			return iter(self.data)
		return self._incremental_caching_iter()
	def _incremental_caching_iter(self):
		indices = itertools.count()
		while True:
			idx = next(indices)
			try:
				yield self.data[idx]
			except IndexError:
				pass
			else:
				continue
			if self.iterator is None:
				return
			try:
				x = next(self.iterator)
				self.data.append(x)
				yield x
			except StopIteration:
				self.iterator = None
	def __reduce__(self):
		# pickle into a list with __reduce__
		# (callable, args, state, listitems)
		return (list, (), None, iter(self))

def UniqueIterator(seq, key=None):
	"""
	yield items of @seq with set semantics; no duplicates

	>>> list(UniqueIterator([1, 2, 3, 3, 5, 1]))
	[1, 2, 3, 5]
	>>> list(UniqueIterator([1, -2, 3, -3, -5, 2], key=abs))
	[1, -2, 3, -5]
	"""
	coll = set()
	if key is None:
		for obj in seq:
			if obj not in coll:
				yield obj
				coll.add(obj)
		return
	else:
		for obj in seq:
			K = key(obj)
			if K not in coll:
				yield obj
				coll.add(K)


if not OrderedDict:
	"""
	The following is:
	http://code.activestate.com/recipes/576693/
	Created by Raymond Hettinger on Wed, 18 Mar 2009 (MIT) 
	Licensed under the MIT License
	"""

	class OrderedDict(dict, DictMixin):

		def __init__(self, *args, **kwds):
			if len(args) > 1:
				raise TypeError('expected at most 1 arguments, got %d' % len(args))
			try:
				self.__end
			except AttributeError:
				self.clear()
			self.update(*args, **kwds)

		def clear(self):
			self.__end = end = []
			end += [None, end, end]         # sentinel node for doubly linked list
			self.__map = {}                 # key --> [key, prev, next]
			dict.clear(self)

		def __setitem__(self, key, value):
			if key not in self:
				end = self.__end
				curr = end[1]
				curr[2] = end[1] = self.__map[key] = [key, curr, end]
			dict.__setitem__(self, key, value)

		def __delitem__(self, key):
			dict.__delitem__(self, key)
			key, prev, next = self.__map.pop(key)
			prev[2] = next
			next[1] = prev

		def __iter__(self):
			end = self.__end
			curr = end[2]
			while curr is not end:
				yield curr[0]
				curr = curr[2]

		def __reversed__(self):
			end = self.__end
			curr = end[1]
			while curr is not end:
				yield curr[0]
				curr = curr[1]

		def popitem(self, last=True):
			if not self:
				raise KeyError('dictionary is empty')
			if last:
				key = next(reversed(self))
			else:
				key = next(iter(self))
			value = self.pop(key)
			return key, value

		def __reduce__(self):
			items = [[k, self[k]] for k in self]
			tmp = self.__map, self.__end
			del self.__map, self.__end
			inst_dict = vars(self).copy()
			self.__map, self.__end = tmp
			if inst_dict:
				return (self.__class__, (items,), inst_dict)
			return self.__class__, (items,)

		def keys(self):
			return list(self)

		setdefault = DictMixin.setdefault
		update = DictMixin.update
		pop = DictMixin.pop
		values = DictMixin.values
		items = DictMixin.items
		iterkeys = DictMixin.iterkeys
		itervalues = DictMixin.itervalues
		iteritems = DictMixin.iteritems

		def __repr__(self):
			if not self:
				return '%s()' % (self.__class__.__name__,)
			return '%s(%r)' % (self.__class__.__name__, list(self.items()))

		def copy(self):
			return self.__class__(self)

		@classmethod
		def fromkeys(cls, iterable, value=None):
			d = cls()
			for key in iterable:
				d[key] = value
			return d

		def __eq__(self, other):
			if isinstance(other, OrderedDict):
				return len(self)==len(other) and list(self.items()) == list(other.items())
			return dict.__eq__(self, other)

		def __ne__(self, other):
			return not self == other

class LruCache (object):
	"""
	Least-recently-used cache mapping of
	size @maxsiz
	"""
	def __init__(self, maxsiz):
		self.d = OrderedDict()
		self.maxsiz = maxsiz

	def __contains__(self, key):
		return key in self.d

	def __setitem__(self, key, value):
		self.d.pop(key, None)
		self.d[key] = value
		if len(self.d) > self.maxsiz:
			# remove the first item (was inserted longest time ago)
			lastkey = next(iter(self.d))
			self.d.pop(lastkey)

	def __getitem__(self, key):
		try:
			value = self.d.pop(key)
		except KeyError:
			raise
		# reinsert the value, puts it "last" in the order
		self.d[key] = value
		return value

if __name__ == '__main__':
	import doctest
	doctest.testmod()
