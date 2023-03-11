"""

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

from __future__ import annotations

import typing as ty
from collections import OrderedDict

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
