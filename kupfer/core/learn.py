from __future__ import annotations

import os
import pickle
import random
import time
import typing as ty
from collections import defaultdict
from pathlib import Path

from kupfer import config
from kupfer.support import conspickle, pretty

if ty.TYPE_CHECKING:
    from kupfer.obj.base import Action, KupferObject, Leaf

__all__ = (
    "add_favorite",
    "erase_object_affinity",
    "get_correlation_bonus",
    "get_object_has_affinity",
    "get_record_score",
    "is_favorite",
    "load",
    "record_action_activations",
    "record_search_hit",
    "remove_favorite",
    "replace_favorites",
    "save",
    "set_correlation",
    "unregister",
)

_MNEMONICS_FILENAME = "mnemonics.pickle"
_CORRELATION_KEY: ty.Final = "kupfer.bonus.correlation"
_ACTIVATIONS_KEY: ty.Final = "kupfer.bonus.activations"

## this is a harmless default
_DEFAULT_ACTIONS: ty.Final = {
    "<kupfer.obj.apps.AppLeaf gnome-terminal>": "<kupfer.obj.apps.LaunchAgain>",
    "<kupfer.obj.apps.AppLeaf xfce4-terminal>": "<kupfer.obj.apps.LaunchAgain>",
}

## Favorites is set of favorites (repr(obj))
_FAVORITES: ty.Final[set[str]] = set()
## _PLUG_FAVS are favorites by plugin; to use must be merged to _FAVORITES
_PLUG_FAVS: ty.Final[dict[str, list[str]]] = {}


class Mnemonics:
    """Class to describe a collection of mnemonics as well as the total count."""

    __slots__ = ("count", "last_ts_used", "mnemonics")

    def __init__(self) -> None:
        self.mnemonics: defaultdict[str, int] = defaultdict(int)
        self.count: int = 0
        self.last_ts_used: int = 0

    def __repr__(self) -> str:
        mnm = ", ".join(f"{m}:{c}" for m, c in self.mnemonics.items())
        return (
            f"<{self.__class__.__name__} cnt={self.count} mnm={mnm}"
            f" ts={self.last_ts_used}>"
        )

    def increment(self, mnemonic: str | None = None) -> None:
        if mnemonic:
            self.mnemonics[mnemonic] += 1

        self.count += 1
        self.last_ts_used = int(time.time())

    def decrement(self) -> None:
        """Decrement total count and the least mnemonic"""
        if self.mnemonics:
            key = min(self.mnemonics.keys(), key=lambda k: self.mnemonics[k])
            if (mcount := self.mnemonics[key]) > 1:
                self.mnemonics[key] = mcount - 1
            else:
                self.mnemonics.pop(key)

        self.count = max(self.count - 1, 0)

    def __bool__(self) -> bool:
        return self.count > 0

    def __getstate__(self) -> dict[str, ty.Any]:
        return {
            "count": self.count,
            "mnemonics": dict(self.mnemonics),
            "last_ts_used": self.last_ts_used,
        }

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        self.count = state.get("count", 0)
        self.last_ts_used = state.get("last_ts_used", 0)
        self.mnemonics = defaultdict(int)
        self.mnemonics.update(state.get("mnemonics", {}))


class Learning:
    @classmethod
    def unpickle_register(cls, pickle_file: str) -> dict[str, ty.Any] | None:
        try:
            pfile = Path(pickle_file).read_bytes()
            data = conspickle.ConservativeUnpickler.loads(pfile)
            assert isinstance(data, dict), "Stored object not a dict"
            pretty.print_debug(__name__, f"Reading from {pickle_file}")
            return data
        except OSError:
            pass
        except (pickle.PickleError, Exception) as exc:
            pretty.print_error(__name__, f"Error loading {pickle_file}: {exc}")

        return None

    @classmethod
    def pickle_register(cls, reg: dict[str, ty.Any], pickle_file: str) -> bool:
        ## Write to tmp then rename over for atomicity
        tmp_pickle_file = f"{pickle_file}.{os.getpid()}"
        pretty.print_debug(__name__, f"Saving to {pickle_file}")
        Path(tmp_pickle_file).write_bytes(
            pickle.dumps(reg, pickle.HIGHEST_PROTOCOL)
        )
        os.rename(tmp_pickle_file, pickle_file)
        return True


# under _CORRELATION_KEY is {str:str}:
#   map repr(action) -> repr(object)
# under _ACTIVATIONS_KEY is {str:(str, int)}:
#   map repr(action) -> (repr(leaf),last usage timestamp)
# other keys keeps Mnemonics
_REGISTER: dict[
    str, Mnemonics | dict[str, str] | dict[str, tuple[str, int]]
] = {}


def _get_register_mnemonics() -> ty.Iterator[tuple[str, Mnemonics]]:
    for leaf, mne in _REGISTER.items():
        if isinstance(mne, Mnemonics):
            yield leaf, mne


def record_search_hit(obj: ty.Any, key: str | None = None) -> None:
    """Record that KupferObject @obj was used, with the optional
    search term @key recording.
    When key is None - skip registration (this is only valid when action is
    performed by accelerator)."""
    if key is None:
        return

    name = repr(obj)
    mns = _REGISTER.get(name)
    if not mns:
        mns = _REGISTER[name] = Mnemonics()

    assert isinstance(mns, Mnemonics)
    mns.increment(key or "")


def get_record_score(obj: ty.Any, key: str = "") -> int:
    """Get total score for KupferObject @obj, bonus score is given for @key
    matches"""
    name = repr(obj)
    fav = 7 if name in _FAVORITES else 0

    mns = _REGISTER.get(name)
    if mns is None:
        return fav

    assert isinstance(mns, Mnemonics)
    if not key:
        return fav + 50 - int(50.0 / (mns.count + 1))

    stats = mns.mnemonics
    closescr = sum(val for m, val in stats.items() if m.startswith(key))
    exact = stats[key]
    mnscore = 80 - int(50.0 / (closescr + 1) + 30.0 / (exact + 1))
    return fav + mnscore


def get_correlation_bonus(obj: Action, for_leaf: Leaf | None) -> int:
    """Get the bonus rank for @obj when used with @for_leaf."""

    # favorites
    rval = ty.cast("dict[str, str]", _REGISTER[_CORRELATION_KEY])
    repr_obj = repr(obj)
    repr_leaf = repr(for_leaf)
    if rval.get(repr_leaf) == repr_obj:
        return 50

    raval = ty.cast("dict[str, tuple[str, int]]", _REGISTER[_ACTIVATIONS_KEY])

    # bonus for last used action for object
    if (val := raval.get(repr_leaf)) and val[0] == repr_obj:
        return 20

    # bonus for last used action for object type
    if (val := raval.get(repr(type(for_leaf)))) and val[0] == repr_obj:
        return 7

    return 0


def set_correlation(obj: Action, for_leaf: Leaf) -> None:
    """Register @obj to get a bonus when used with @for_leaf."""
    rval = ty.cast("dict[str, str]", _REGISTER[_CORRELATION_KEY])
    rval[repr(for_leaf)] = repr(obj)


def record_action_activations(obj: Action, for_leaf: Leaf) -> None:
    """Record action activation for leaf that boost this action in next search.
    Also registered is object class so using this action for similar object
    also get some (smaller) bonus."""

    rval = ty.cast("dict[str, tuple[str, int]]", _REGISTER[_ACTIVATIONS_KEY])

    repr_obj = repr(obj)
    now = int(time.time())
    rval[repr(for_leaf)] = (repr_obj, now)
    rval[repr(type(for_leaf))] = (repr_obj, now)


def get_object_has_affinity(obj: Leaf) -> bool:
    """Return if @obj has any positive score in the register."""
    robj = repr(obj)
    return bool(
        _REGISTER.get(robj) or _REGISTER[_CORRELATION_KEY].get(robj)  # type: ignore
    )


def erase_object_affinity(obj: Leaf) -> None:
    """Remove all track of affinity for @obj."""
    robj = repr(obj)
    _REGISTER.pop(robj, None)
    _REGISTER[_CORRELATION_KEY].pop(robj, None)  # type: ignore


def _prune_register(goalitems: int = 500) -> None:
    """Try to reduce number of mnemonic to `goalitems`.

    in first pass try to delete oldest mnemonics with score == 1.

    Then, remove items with chance (len/25000)

    Assuming homogeneous records (all with score one) we keep:
    x_n+1 := x_n * (1 - chance)

    To this we have to add the expected number of added mnemonics per
    invocation, est. 10, and we can estimate a target number of saved mnemonics.
    """

    # get all items sorted by last used time
    items: list[tuple[int, str, Mnemonics]] = sorted(
        (mne.last_ts_used, leaf, mne)
        for leaf, mne in _get_register_mnemonics()
    )
    to_del = []
    to_del_cnt = len(items) - goalitems
    for _ts, leaf, mne in items:
        mne.decrement()
        if not mne:
            to_del.append(leaf)
            to_del_cnt -= 1
            if not to_del_cnt:
                break

    for leaf in to_del:
        _REGISTER.pop(leaf)

    pretty.print_debug(
        __name__,
        f"Pruned register ({len(_REGISTER)} mnemonics, {len(to_del)} oldest deleted)",
    )

    if len(_REGISTER) <= goalitems:
        return

    random.seed()
    rand = random.random

    flux = 2.0
    alpha = flux / goalitems**2

    chance = min(0.1, len(_REGISTER) * alpha)
    to_del = []
    for leaf, mne in _get_register_mnemonics():
        if rand() <= chance:
            assert isinstance(mne, Mnemonics)
            mne.decrement()
            if not mne:
                to_del.append(leaf)

    for leaf in to_del:
        _REGISTER.pop(leaf)

    pretty.print_debug(
        __name__,
        f"Pruned register ({len(_REGISTER)} mnemonics, {len(to_del)} deleted)",
    )


def _purge_action_reg(goalitems: int) -> None:
    """Purge action usage - remove oldest items up to `goalitems` count"""
    raval = ty.cast("dict[str, tuple[str, int]]", _REGISTER[_ACTIVATIONS_KEY])
    if len(raval) <= goalitems:
        return

    to_delkv = sorted((ts, key) for key, (_obj, ts) in raval.items())
    # delete oldest entries up to goalitems
    for _ts, key in to_delkv[: len(raval) - goalitems]:
        raval.pop(key)


def load() -> None:
    """Load learning database."""
    _REGISTER.clear()

    if (filepath := config.get_config_file(_MNEMONICS_FILENAME)) and (
        reg := Learning.unpickle_register(filepath)
    ):
        _REGISTER.update(reg)

    if _CORRELATION_KEY not in _REGISTER:
        _REGISTER[_CORRELATION_KEY] = _DEFAULT_ACTIONS

    if _ACTIVATIONS_KEY not in _REGISTER:
        _REGISTER[_ACTIVATIONS_KEY] = ty.cast("dict[str, tuple[str, int]]", {})


_MAX_REGISTER_SIZE: ty.Final[int] = 500


def save() -> None:
    """Save the learning record."""
    if not _REGISTER:
        pretty.print_debug(__name__, "Not writing empty register")
        return

    _purge_action_reg(_MAX_REGISTER_SIZE)
    if len(_REGISTER) > _MAX_REGISTER_SIZE:
        _prune_register(_MAX_REGISTER_SIZE)

    filepath = config.save_config_file(_MNEMONICS_FILENAME)
    assert filepath
    Learning.pickle_register(_REGISTER, filepath)


def _rebuild_favorites():
    """Build _FAVORITES set from _PLUG_FAVS buckets."""
    _FAVORITES.clear()
    for favs in _PLUG_FAVS.values():
        _FAVORITES.update(favs)


def add_favorite(plugin_id: str, *objs: KupferObject) -> None:
    """Add favorites `objs` to `plugin_id` bucket."""
    fset = _PLUG_FAVS.get(plugin_id)
    if fset:
        # filter and add new obj
        nfset = [obj for obj in map(repr, objs) if obj not in fset]
        fset.extend(nfset)
    else:
        nfset = _PLUG_FAVS[plugin_id] = list(map(repr, objs))

    _FAVORITES.update(nfset)


def replace_favorites(plugin_id: str, *objs: KupferObject) -> None:
    """Replace favorites in `plugin_id` bucket. If no `objs` remove all
    favorites for `plugin_id`."""
    if not objs:
        if plugin_id in _PLUG_FAVS:
            del _PLUG_FAVS[plugin_id]
            _rebuild_favorites()

        return

    fset = _PLUG_FAVS[plugin_id] = list(map(repr, objs))
    _FAVORITES.update(fset)


def remove_favorite(plugin_id: str, obj: KupferObject) -> None:
    """Remove `obj` from favorites in `plugin_id` bucket."""
    if fset := _PLUG_FAVS.get(plugin_id):
        try:
            fset.remove(repr(obj))
        except ValueError:
            return

        if fset:
            _PLUG_FAVS[plugin_id] = fset
        else:
            del _PLUG_FAVS[plugin_id]

        _rebuild_favorites()


def is_favorite(obj: KupferObject) -> bool:
    return repr(obj) in _FAVORITES


def unregister(obj):
    _REGISTER.pop(obj, None)
