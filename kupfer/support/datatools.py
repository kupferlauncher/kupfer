import itertools
import typing as ty
from collections import OrderedDict

T = ty.TypeVar("T")


class SavedIterable(ty.Generic[T]):
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

    def __new__(cls, iterable: ty.Iterable[T]) -> ty.Any:
        if isinstance(iterable, list):
            return iterable

        return object.__new__(cls)

    def __init__(self, iterable: ty.Iterable[T]) -> None:
        self.iterator: ty.Optional[ty.Iterator[T]] = iter(iterable)
        self.data: list[T] = []

    def __iter__(self) -> ty.Iterator[T]:
        if self.iterator is None:
            return iter(self.data)

        return self._incremental_caching_iter()

    def _incremental_caching_iter(self) -> ty.Iterator[T]:
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

    def __reduce__(self) -> ty.Tuple[ty.Any, ...]:
        # pickle into a list with __reduce__
        # (callable, args, state, listitems)
        return (list, (), None, iter(self))


def unique_iterator(
    seq: ty.Iterable[T],
    key: ty.Optional[ty.Callable[[T], ty.Any]] = None,
) -> ty.Iterator[T]:
    """
    yield items of @seq with set semantics; no duplicates

    >>> list(unique_iterator([1, 2, 3, 3, 5, 1]))
    [1, 2, 3, 5]
    >>> list(unique_iterator([1, -2, 3, -3, -5, 2], key=abs))
    [1, -2, 3, -5]
    """
    coll = set()
    if key is None:
        for obj in seq:
            if obj not in coll:
                yield obj
                coll.add(obj)

        return

    for obj in seq:
        if (value := key(obj)) not in coll:
            yield obj
            coll.add(value)


K = ty.TypeVar("K")
V = ty.TypeVar("V")


class LruCache(ty.Generic[K, V]):
    """
    Least-recently-used cache mapping of
    size @maxsiz
    """

    def __init__(self, maxsiz: int) -> None:
        self._data: OrderedDict[K, V] = OrderedDict()
        self._maxsize = maxsiz

    def __contains__(self, key: K) -> bool:
        return key in self._data

    def __setitem__(self, key: K, value: V) -> None:
        try:
            self._data.move_to_end(key, last=True)
        except KeyError:
            self._data[key] = value

            if len(self._data) > self._maxsize:
                # remove the first item (was inserted longest time ago)
                self._data.popitem(last=False)

    def __getitem__(self, key: K) -> V:
        value = self._data.pop(key)
        self._data.move_to_end(key, last=True)
        return value

    def items(self):
        return self._data.items()


if __name__ == "__main__":
    import doctest

    doctest.testmod()
