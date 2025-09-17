from __future__ import annotations

import os
import pickle
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
        last_used = (time.time() - self.last_ts_used) // 86400
        return (
            f"<{self.__class__.__name__} cnt={self.count} mnm={mnm}"
            f" ts={self.last_ts_used} ({last_used}d ago)>"
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

    def stats_for_key(self, key: str) -> int:
        if not key:
            # if no key, score depend on number of mnemonic usage (count)
            return 50 - 50 // (self.count + 1)

        closescr = sum(
            val for m, val in self.mnemonics.items() if m.startswith(key)
        )
        exact = self.mnemonics.get(key, 0)
        return 80 - int(50.0 / (closescr + 1) + 30.0 / (exact + 1))

    def prune(self) -> None:
        keys_to_del = [k for k, c in self.mnemonics.items() if c == 0]
        for k in keys_to_del:
            del self.mnemonics[k]

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


_MAX_MNEMONICS_COUNT: ty.Final[int] = 500
_MAX_CORRELATIONS_COUNT: ty.Final[int] = 100
_MAX_ACTIONS_COUNT: ty.Final[int] = 100


class _Register:
    def __init__(self) -> None:
        self.correlations: dict[str, tuple[str, int]] = {}
        self.activations: dict[str, tuple[str, int]] = {}
        self.mnemonics: defaultdict[str, Mnemonics] = defaultdict(Mnemonics)

    def __bool__(self) -> bool:
        return (
            bool(self.correlations)
            or bool(self.activations)
            or bool(self.mnemonics)
        )

    def prune(self) -> None:
        self._purge_action_reg(_MAX_ACTIONS_COUNT)
        self._purge_correlations_reg(_MAX_CORRELATIONS_COUNT)
        self._prune_register(_MAX_MNEMONICS_COUNT)

    def _prune_register_unused(self) -> None:
        """Prune unused mnemonics: remove mnemonics keys with 0 value, remove
        whole mnemonic with count == 0. This clean mnemonics create by bug
        in code...
        """
        for m in self.mnemonics.values():
            m.prune()

        to_del = [k for k, m in self.mnemonics.items() if not m.count]
        for leaf in to_del:
            del self.mnemonics[leaf]

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(self.mnemonics)} mnemonics, {len(to_del)} unused)",
        )

    def _prune_register_decrement(self, goalitems: int) -> None:
        """Decrement mnemonics sorted by last use time; if mnemonic count == 0
        remove it."""

        # get all items sorted by last used time
        items: list[tuple[int, str, Mnemonics]] = sorted(
            (mne.last_ts_used, leaf, mne)
            for leaf, mne in self.mnemonics.items()
        )
        to_del = []
        to_del_cnt = len(items) - goalitems

        for _ts, leaf, mne in items:
            mne.decrement()
            if not mne.count:
                to_del.append(leaf)
                to_del_cnt -= 1
                if not to_del_cnt:
                    break

        for leaf in to_del:
            del self.mnemonics[leaf]

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(self.mnemonics)} mnemonics, "
            f"{len(to_del)} oldest deleted)",
        )

    def _prune_register_least_used(self, goalitems: int) -> None:
        # get all items sorted by last used time
        to_del: list[tuple[int, str]] = sorted(
            (mne.count, leaf) for leaf, mne in self.mnemonics.items()
        )

        for _cnt, leaf in to_del[: len(self.mnemonics) - goalitems]:
            del self.mnemonics[leaf]

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(self.mnemonics)} mnemonics, "
            f"{len(to_del)} least used)",
        )

    def _prune_register(self, goalitems: int = 50) -> None:
        """Try to reduce number of mnemonic to `goalitems`.

        To reach `goalitems`:
        1. delete unused/broken mnemonics (count=0)
        2. from oldest mnemonics - decrement count & mnemonics usage; delete
           mnemonics with count == 0
        3. delete least used
        """
        if len(self.mnemonics) < goalitems:
            pretty.print_debug(
                __name__,
                "Pruned mnemonics register not required "
                f"({len(self.mnemonics)} / {goalitems})",
            )
            return

        self._prune_register_unused()

        if len(self.mnemonics) <= goalitems:
            return

        self._prune_register_decrement(goalitems)

        if len(self.mnemonics) <= goalitems:
            return

        self._prune_register_least_used(goalitems)

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(self.mnemonics)} mnemonics.",
        )

    def _purge_action_reg(self, goalitems: int) -> None:
        """Purge action usage - remove oldest items up to `goalitems` count"""
        raval = self.activations
        if len(raval) <= goalitems:
            return

        to_delkv = sorted((ts, key) for key, (_obj, ts) in raval.items())
        # delete oldest entries up to goalitems
        for _ts, key in to_delkv[: len(raval) - goalitems]:
            del raval[key]

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(raval)} activiations, {len(to_delkv)})",
        )

    def _purge_correlations_reg(self, goalitems: int) -> None:
        """Purge correlations - remove oldest items up to `goalitems` count"""
        raval = self.correlations
        if len(raval) <= goalitems:
            return

        to_delkv = sorted((ts, key) for key, (_obj, ts) in raval.items())
        # delete oldest entries up to goalitems
        for _ts, key in to_delkv[: len(raval) - goalitems]:
            del raval[key]

        pretty.print_debug(
            __name__,
            f"Pruned register ({len(raval)} correlations, {len(to_delkv)})",
        )


_REGISTER = _Register()


def record_search_hit(obj: ty.Any, key: str | None = None) -> None:
    """Record that KupferObject @obj was used, with the optional
    search term @key recording.
    When key is None - skip registration (this is only valid when action is
    performed by accelerator)."""
    if key is not None:
        _REGISTER.mnemonics[repr(obj)].increment(key)


def get_record_score(obj: ty.Any, key: str = "") -> int:
    """Get total score for KupferObject @obj, bonus score is given for @key
    matches"""
    name = repr(obj)
    fav = 7 if name in _FAVORITES else 0

    if mns := _REGISTER.mnemonics.get(name):
        return fav + mns.stats_for_key(key)

    return fav


def get_correlation_bonus(obj: Action, for_leaf: Leaf | None) -> int:
    """Get the bonus rank for @obj when used with @for_leaf."""
    # favorites
    repr_obj = repr(obj)
    repr_leaf = repr(for_leaf)
    if (v := _REGISTER.correlations.get(repr_leaf)) and v[0] == repr_obj:
        return 50

    raval = _REGISTER.activations

    # bonus for last used action for object
    if (val := raval.get(repr_leaf)) and val[0] == repr_obj:
        return 20

    # bonus for last used action for object type
    if (val := raval.get(repr(type(for_leaf)))) and val[0] == repr_obj:
        return 7

    return 0


def set_correlation(obj: Action, for_leaf: Leaf) -> None:
    """Register @obj to get a bonus when used with @for_leaf."""
    _REGISTER.correlations[repr(for_leaf)] = (repr(obj), int(time.time()))


def record_action_activations(obj: Action, for_leaf: Leaf) -> None:
    """Record action activation for leaf that boost this action in next search.
    Also registered is object class so using this action for similar object
    also get some (smaller) bonus."""

    repr_for_leaf = repr(for_leaf)
    repr_obj = repr(obj)

    _REGISTER.activations[repr_for_leaf] = _REGISTER.activations[
        repr(type(for_leaf))
    ] = (repr_obj, int(time.time()))

    # update correlation bonus timestamp (if exists), so we keep track
    # when last given correlation was used.
    if (v := _REGISTER.correlations.get(repr_for_leaf)) and v[0] == repr_obj:
        _REGISTER.correlations[repr_for_leaf] = (repr_obj, int(time.time()))


def get_object_has_affinity(obj: Leaf) -> bool:
    """Return if @obj has any positive score in the register."""
    robj = repr(obj)
    return bool(
        _REGISTER.mnemonics.get(robj)
        or _REGISTER.correlations.get(robj)
        or _REGISTER.activations.get(robj)
    )


def erase_object_affinity(obj: Leaf) -> None:
    """Remove all track of affinity for @obj."""
    robj = repr(obj)
    _REGISTER.mnemonics.pop(robj, None)
    _REGISTER.correlations.pop(robj, None)


def load() -> None:
    """Load learning database."""
    if (filepath := config.get_config_file(_MNEMONICS_FILENAME)) and (
        reg := Learning.unpickle_register(filepath)
    ):
        _REGISTER.activations = reg.pop(_ACTIVATIONS_KEY) or {}

        corrs = reg.pop(_CORRELATION_KEY) or _DEFAULT_ACTIONS
        # check if this is old file format (values are strings)
        if isinstance(next(iter(corrs.values())), str):
            # update data
            now = int(time.time())
            _REGISTER.correlations = {k: (v, now) for k, v in corrs.items()}
        else:
            _REGISTER.correlations = ty.cast(
                "dict[str, tuple[str, int]]", corrs
            )

        _REGISTER.mnemonics.clear()
        _REGISTER.mnemonics.update(reg)


def save() -> None:
    """Save the learning record."""

    if not _REGISTER:
        pretty.print_debug(__name__, "Not writing empty register")
        return

    _REGISTER.prune()

    filepath = config.save_config_file(_MNEMONICS_FILENAME)

    # legacy file format:
    # under _CORRELATION_KEY is {str:str}:
    #   map repr(action) -> repr(object)
    # under _ACTIVATIONS_KEY is {str:(str, int)}:
    #   map repr(action) -> (repr(leaf),last usage timestamp)
    # other keys keeps Mnemonics

    assert filepath
    reg: dict[str, ty.Any] = _REGISTER.mnemonics.copy()
    reg[_ACTIVATIONS_KEY] = _REGISTER.activations
    reg[_CORRELATION_KEY] = _REGISTER.correlations
    Learning.pickle_register(reg, filepath)


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
    _REGISTER.mnemonics.pop(obj, None)
