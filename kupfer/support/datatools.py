"""
This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import inspect
import typing as ty
from collections import OrderedDict
import functools

K = ty.TypeVar("K")
V = ty.TypeVar("V")
VD = ty.TypeVar("VD")


def _get_point_of_create(offset: int = 2) -> str:
    """Find information about function caller with `offset` in tracestack."""
    for frame in inspect.stack()[offset:]:
        if "kupfer" in frame.filename:
            return f"{frame.filename}:{frame.lineno}"

    return "?"


_sentinel = object()


class LruCache(ty.Generic[K, V]):
    """Least-recently-used cache mapping of size *maxsize*.

    *name* is optional cache name for debug purpose. If not given, is place
    when cache is created (filename:lineno).
    """

    def __init__(self, maxsize: int, name: str | None = None) -> None:
        super().__init__()
        self._data: OrderedDict[K, V] = OrderedDict()
        self._maxsize = maxsize
        self._name = name or _get_point_of_create()
        self._hit = 0
        self._miss = 0
        self._inserts = 0

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, key: K, value: V) -> None:
        self._inserts += 1
        # set add item on the end of dict
        data = self._data
        if key in self._data:
            # check is item already in dict by trying to move it to the end
            data.move_to_end(key, last=True)
        else:
            # item not found in dict so add it
            data[key] = value

            if len(data) > self._maxsize:
                # remove the first item (was inserted longest time ago)
                data.popitem(last=False)

    def __getitem__(self, key: K) -> V:
        # try to get item from dict, if not found KeyError is raised
        try:
            value = self._data[key]
        except KeyError as err:
            self._miss += 1
            raise err

        self._hit += 1
        # found, so move it to the end
        self._data.move_to_end(key, last=True)
        return value

    def get(self, key: K, default: V | VD | None = None) -> V | VD | None:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> ty.KeysView[K]:
        return self._data.keys()

    def values(self) -> ty.ValuesView[V]:
        return self._data.values()

    def items(self) -> ty.ItemsView[K, V]:
        return self._data.items()

    def clear(self) -> None:
        self._data.clear()

    def __str__(self) -> str:
        return (
            f"<LruCache '{self._name}': maxsize={self._maxsize}, "
            f"items={len(self)}, hit={self._hit}, miss={self._miss}, "
            f"inserts={self._inserts}>"
        )

    def get_or_insert(self, key: K, creator: ty.Callable[[], V]) -> V:
        """Get value from cache. If not exists - create with with `creator`
        function and insert into cache."""
        try:
            val = self._data[key]
        except KeyError:
            self._miss += 1
            self._inserts += 1
            val = self._data[key] = creator()
        else:
            self._hit += 1

        return val


RT = ty.TypeVar("RT")  # return type


class simple_cache(ty.Generic[RT]):  # pylint: disable=invalid-name
    """Function wrapper that remember (cache) one result and return it
    if no arguments changed.

    Wrapper properties:
        *cache_current_args*   remembered (last) arguments
        *cache_current_value*  remembered (last) function result
        *cache_hit*            number of result returned from cache
        *cache_miss*           number of wrapped function calls

    Usage::

        @SimpleCache
        def function(args):
            ...
    """

    cache_current_value: RT
    cache_current_args: ty.Any
    cache_hit: int
    cache_miss: int

    def __init__(self, func: ty.Callable[..., RT]):
        """Create SimpleCache for *func* function."""
        functools.update_wrapper(self, func)
        self.func = func
        self.cache_clear()
        self.name = _get_point_of_create()

    def __call__(self, *args: ty.Any, **kwargs: ty.Any) -> RT:
        if self.cache_current_args == (args, kwargs):
            self.cache_hit += 1
            return self.cache_current_value

        result = self.func(*args, **kwargs)

        self.cache_current_args = (args, kwargs)
        self.cache_current_value = result
        self.cache_miss += 1

        return result

    def cache_clear(self) -> None:
        """Clear cache and stats."""
        self.cache_current_value = None  # type: ignore
        self.cache_current_args = None
        self.cache_hit = 0
        self.cache_miss = 0

    def __str__(self) -> str:
        return (
            f"<simple_cache '{self.name}': hit={self.cache_hit},"
            f" miss={self.cache_miss}>"
        )


def evaluate_once(func: ty.Callable[..., RT]) -> ty.Callable[..., RT]:
    """Decorator that run wrapped function once and always return computed
    value. No thread safe."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = getattr(wrapper, "cached_value", _sentinel)
        if result is not _sentinel:
            return result

        result = func(*args, **kwargs)
        setattr(wrapper, "cached_value", result)
        return result

    return wrapper
