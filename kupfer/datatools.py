import itertools

from collections import OrderedDict

class SavedIterable (object):
    """Wrap an iterable and cache it.

    The SavedIterable can be accessed streamingly, while still being
    incrementally cached. Later attempts to iterate it will access the
    whole of the sequence.

    When it has been cached to its full extent once, it reduces to a
    thin wrapper of a sequence iterator. The SavedIterable will pickle
    into a list.

    >>> s = SavedIterable(range(5))
    >>> next(iter(s))
    0
    >>> list(s)
    [0, 1, 2, 3, 4]

    >>> iter(s)   # doctest: +ELLIPSIS
    <list_iterator object at 0x...>

    >>> import pickle
    >>> pickle.loads(pickle.dumps(s))
    [0, 1, 2, 3, 4]

    >>> u = SavedIterable(list(range(5)))
    >>> one, two = iter(u), iter(u)
    >>> next(one), next(two)
    (0, 0)
    >>> list(two)
    [1, 2, 3, 4]
    >>> list(one)
    [1, 2, 3, 4]

    >>> SavedIterable(list(range(3)))
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
