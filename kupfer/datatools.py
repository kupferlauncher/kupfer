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

	>>> SavedIterable(range(3))
	[0, 1, 2]
	"""
	def __new__(self, iterable):
		if isinstance(iterable, list):
			return iterable
		return object.__new__(self)
	def __init__(self, iterable):
		self.iterator = iter(iterable)
		self.data = []
	def __iter__(self):
		if self.iterator is None:
			return iter(self.data)
		return self._incremental_caching_iter()
	def _incremental_caching_iter(self):
		for x in self.data:
			yield x
		for x in self.iterator:
			self.data.append(x)
			yield x
		self.iterator = None
	def __reduce__(self):
		# pickle into a list with __reduce__
		# (callable, args, state, listitems)
		return (list, (), None, iter(self))

if __name__ == '__main__':
	import doctest
	doctest.testmod()
