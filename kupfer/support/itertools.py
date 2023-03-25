#! /usr/bin/env python3
# Distributed under terms of the GPLv3 license.
"""
Support function for iterators

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

from __future__ import annotations

import itertools
import typing as ty


def two_part_mapper(instr: str, repfunc: ty.Callable[[str], str | None]) -> str:
    """
    Scan @instr two characters at a time and replace using @repfunc.
    If @repfunc return not None - use origin character.
    """
    if not instr:
        return instr

    def _inner():
        sit = zip(instr, instr[1:])
        for cur, nex in sit:
            key = cur + nex
            if (rep := repfunc(key)) is not None:
                yield rep
                # skip a step in the iter
                try:
                    next(sit)
                except StopIteration:
                    return

            else:
                yield cur

        yield instr[-1]

    return "".join(_inner())


T = ty.TypeVar("T")


def peekfirst(
    seq: ty.Iterable[T],
) -> tuple[T | None, ty.Iterable[T]]:
    """This function will return (firstitem, iter) where firstitem is the first
    item of `seq` or None if empty, and iter an equivalent copy of `seq`
    """
    seq = iter(seq)
    for itm in seq:
        old_iter = itertools.chain((itm,), seq)
        return (itm, old_iter)

    return (None, seq)


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
        self.iterator: ty.Iterator[T] | None = iter(iterable)
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

    def __reduce__(self) -> tuple[ty.Any, ...]:
        # pickle into a list with __reduce__
        # (callable, args, state, listitems)
        return (list, (), None, iter(self))


def unique_iterator(
    seq: ty.Iterable[T],
    key: ty.Callable[[T], ty.Any] | None = None,
) -> ty.Iterator[T]:
    """Yield items of `seq` with set semantics; no duplicates.
    If `key` is given, value of key(object) is used for detecting duplicates.

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


def as_list(seq: ty.Iterable[T]) -> ty.Collection[T]:
    """Return a list out of @seq, or seq if it is a list"""
    if isinstance(seq, (list, tuple)):
        return seq

    return list(seq)


if __name__ == "__main__":
    import doctest

    doctest.testmod()