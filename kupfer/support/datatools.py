"""

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

from __future__ import annotations
import inspect
import typing as ty
from collections import OrderedDict

K = ty.TypeVar("K")
V = ty.TypeVar("V")


def _get_point_of_create(offset: int = 2) -> str:
    for frame in inspect.stack()[offset:]:
        if "kupfer" in frame.filename:
            return f"{frame.filename}:{frame.lineno}"

    return "?"


class LruCache(OrderedDict[K, V]):
    """
    Least-recently-used cache mapping of size `maxsiz`.

    `name` is optional cache name for debug purpose. If not defined - is place
    when cache is created (filename:lineno).
    """

    def __init__(self, maxsiz: int, name: str | None = None) -> None:
        super().__init__()
        self._maxsize = maxsiz
        self._name = name or _get_point_of_create()

    def __setitem__(self, key: K, value: V) -> None:
        # set add item on the end of dict
        try:
            # check is item already in dict by trying to move it to the end
            self.move_to_end(key, last=True)
        except KeyError:
            # item not found in dict so add it
            super().__setitem__(key, value)

            if len(self) > self._maxsize:
                # remove the first item (was inserted longest time ago)
                self.popitem(last=False)

    def __getitem__(self, key: K) -> V:
        # try to get item from dict, if not found KeyError is raised
        value = super().__getitem__(key)
        # found, so move it to the end
        self.move_to_end(key, last=True)
        return value

    def __str__(self) -> str:
        return (
            f"<LruCache '{self._name}': maxsize={self._maxsize}, "
            f"items={len(self)}>"
        )

    def get_or_insert(self, key: K, creator: ty.Callable[[], V]) -> V:
        """Get value from cache. If not exists - create with with `creator`
        function and insert into cache."""
        try:
            return self[key]
        except KeyError:
            val = self[key] = creator()
            return val
