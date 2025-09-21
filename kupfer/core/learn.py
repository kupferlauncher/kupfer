from __future__ import annotations

import os
import pickle
import time
import typing as ty
from collections import defaultdict
from contextlib import suppress
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
_MNEMONICS_KEY: ty.Final = "kupfer.bonus.mnemonics"
_CORRELATION_KEY: ty.Final = "kupfer.bonus.correlation"
_CORRELATION2_KEY: ty.Final = "kupfer.bonus.correlation2"
_ACTIVATIONS_KEY: ty.Final = "kupfer.bonus.activations"


# limit number of stored items in Registry
_MAX_MNEMONICS_COUNT: ty.Final[int] = 500
_MAX_CORRELATIONS_COUNT: ty.Final[int] = 100
_MAX_CORRELATION_ACTIONS: ty.Final[int] = 10


## this is a harmless default
_DEFAULT_ACTIONS: ty.Final = {
    "<kupfer.obj.apps.AppLeaf gnome-terminal>": "<kupfer.obj.apps.LaunchAgain>",
    "<kupfer.obj.apps.AppLeaf xfce4-terminal>": "<kupfer.obj.apps.LaunchAgain>",
}

# skip this actions when recording correlations
_IGNORED_ACTIONS: ty.Final = {
    "<kupfer.plugin.core.Rescan>",
    "<kupfer.plugin.applications.SetDefaultApplication>",
    "<kupfer.plugin.core.debug.DebugInfo>",
}

## Favorites is set of favorites (repr(obj))
_FAVORITES: ty.Final[set[str]] = set()
## _PLUG_FAVS are favorites by plugin; to use must be merged to _FAVORITES
_PLUG_FAVS: ty.Final[dict[str, list[str]]] = {}


class Mnemonics:
    """Class to describe a collection of mnemonics as well as the total count."""

    __slots__ = ("count", "last_ts_used", "mnemonics")

    def __init__(self) -> None:
        # map word -> number of uses
        self.mnemonics: defaultdict[str, int] = defaultdict(int)
        # total number of uses
        self.count: int = 0
        # last update timestamp
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

    def score_for_key(self, key: str) -> int:
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
            "mnemonics": self.mnemonics,
            "last_ts_used": self.last_ts_used,
        }

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        self.count = state.get("count", 0)
        self.last_ts_used = state.get("last_ts_used", 0)
        self.mnemonics = defaultdict(int, state.get("mnemonics", {}))


class Correlation:
    """Correlation map leaf into actions. There should be no more than couple
    of actions."""

    __slots__ = ("actions", "last_ts_used", "permanent_action")

    def __init__(self, /, *actions: str) -> None:
        # list of actions sorted by usage (first item in list is last used
        # action)
        self.actions: list[str] = list(actions)
        # if user set this correlation this is permanent action and have extra
        # bonus
        self.permanent_action: str | None = None
        # last used timestamp
        self.last_ts_used: int = 0

    def __repr__(self) -> str:
        last_used = (time.time() - self.last_ts_used) // 86400
        return (
            f"<{self.__class__.__name__} actions={self.actions} "
            f"permanent_action={self.permanent_action} "
            f"ts={self.last_ts_used} ({last_used}d ago)>"
        )

    def score_for_action(self, action: str) -> int:
        """Score correlation for action; permanent_action give const bonus,
        for other actions - score depend on last use of given action."""
        if action == self.permanent_action:
            return 50

        for idx, a in enumerate(self.actions):
            if a == action:
                return max(1, 20 - idx)

        return 0

    def update(self, key: str) -> None:
        self.last_ts_used = int(time.time())

        if key == self.permanent_action:
            # do no update actions when action is set as permanent
            return

        with suppress(ValueError):
            self.actions.remove(key)

        self.actions.insert(0, key)

        if len(self.actions) > _MAX_CORRELATION_ACTIONS:
            self.actions.pop(-1)

    def update_permanent_action(self, key: str) -> None:
        self.permanent_action = key
        self.last_ts_used = int(time.time())


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


class _Register:
    def __init__(self) -> None:
        # correlations map leaf  to action
        self.correlations: defaultdict[str, Correlation] = defaultdict(
            Correlation
        )
        # mnemonics map object into Mnemonics; each mnemonic has map list of
        # words used to activate object with number of activations.
        self.mnemonics: defaultdict[str, Mnemonics] = defaultdict(Mnemonics)

    def __bool__(self) -> bool:
        return bool(self.correlations) or bool(self.mnemonics)

    def prune(self) -> None:
        self._prune_mnemonics(_MAX_MNEMONICS_COUNT)
        self._prune_correlations(_MAX_CORRELATIONS_COUNT)
        pretty.print_debug(
            __name__,
            f"Register after prune: correlations: {len(self.correlations)}, "
            f"mnemonics: {len(self.mnemonics)}.",
        )

    def _prune_correlations(self, goalitems: int) -> None:
        """Prune  old correlations up to @goalitems. This clean register
        from items for not existing any more leaves. Keep correlation
        with user-defined actions."""

        if len(self.correlations) < goalitems:
            pretty.print_debug(
                __name__,
                "Pruned correlations register not required "
                f"({len(self.correlations)} / {goalitems})",
            )
            return

        items: list[tuple[int, str]] = sorted(
            (c.last_ts_used, leaf)
            for leaf, c in self.correlations.items()
            if not c.permanent_action
        )

        to_del = items[: len(items) - goalitems]
        for _ts, leaf in to_del:
            del self.correlations[leaf]

        pretty.print_debug(
            __name__,
            "Pruned correlation from register; deleted: {len(to_del)})",
        )

    def _prune_mnemonics_unused(self) -> None:
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
            f"Pruned unused mnemonics from register; deleted: {len(to_del)}",
        )

    def _prune_mnemonics_decrement(self, goalitems: int) -> None:
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
            f"Pruned mnemonics from register; deleted: {len(to_del)}",
        )

    def _prune_mnemonics_least_used(self, goalitems: int) -> None:
        # get all items sorted by last used time
        items: list[tuple[int, str]] = sorted(
            (mne.count, leaf) for leaf, mne in self.mnemonics.items()
        )

        to_del = items[: len(self.mnemonics) - goalitems]
        for _cnt, leaf in to_del:
            del self.mnemonics[leaf]

        pretty.print_debug(
            __name__,
            f"Pruned least used mnemonics from register; deleted: {len(to_del)}",
        )

    def _prune_mnemonics(self, goalitems: int = 50) -> None:
        """Try to reduce number of mnemonic to `goalitems`.

        Always delete unused/broken mnemonics (count=0)

        To reach `goalitems`:
        1. from oldest mnemonics - decrement count & mnemonics usage; delete
           mnemonics with count == 0
        2. delete least used
        """
        self._prune_mnemonics_unused()

        if len(self.mnemonics) < goalitems:
            pretty.print_debug(
                __name__,
                "Pruned mnemonics register not required "
                f"({len(self.mnemonics)} / {goalitems})",
            )
            return

        if len(self.mnemonics) > goalitems:
            self._prune_mnemonics_decrement(goalitems)

        if len(self.mnemonics) > goalitems:
            self._prune_mnemonics_least_used(goalitems)


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
        return fav + mns.score_for_key(key)

    return fav


def get_correlation_bonus(action: Action, for_leaf: Leaf | None) -> int:
    """Get the bonus rank for @obj when used with @for_leaf."""
    # favorites
    repr_action = repr(action)
    repr_leaf = repr(for_leaf)

    # get bonus for exact match leaf -> action or user defined
    # correlation for leaf and action
    if (c := _REGISTER.correlations.get(repr_leaf)) and (
        s := c.score_for_action(repr_action)
    ):
        return s

    # get bonus for match type of leaf -> action
    if (c := _REGISTER.correlations.get(repr(type(for_leaf)))) and (
        s := c.score_for_action(repr_action)
    ):
        return s // 2

    return 0


def set_correlation(action: Action, for_leaf: Leaf) -> None:
    """Register @obj to get a bonus when used with @for_leaf."""
    repr_for_leaf = repr(for_leaf)
    repr_action = repr(action)
    _REGISTER.correlations[repr_for_leaf].update_permanent_action(repr_action)


def record_action_activations(action: Action, for_leaf: Leaf) -> None:
    """Record action activation for leaf that boost this action in next search.
    Also registered is object class so using this action for similar object
    also get some (smaller) bonus."""

    repr_action = repr(action)

    if repr_action in _IGNORED_ACTIONS:
        return

    _REGISTER.correlations[repr(for_leaf)].update(repr_action)
    _REGISTER.correlations[repr(type(for_leaf))].update(repr_action)


def get_object_has_affinity(obj: Leaf) -> bool:
    """Return if @obj has any positive score in the register."""
    robj = repr(obj)
    return bool(robj in _REGISTER.mnemonics or robj in _REGISTER.correlations)


def erase_object_affinity(obj: Leaf) -> None:
    """Remove all track of affinity for @obj."""
    robj = repr(obj)
    _REGISTER.mnemonics.pop(robj, None)
    _REGISTER.correlations.pop(robj, None)


def _upgrade_and_fill_register(reg: dict[str, ty.Any]) -> None:
    """Update correlation stored in old format."""
    _REGISTER.correlations.clear()
    _REGISTER.mnemonics.clear()

    # old format - activations
    if acts := reg.pop(_ACTIVATIONS_KEY, None):
        _REGISTER.correlations.update(
            {
                lr: Correlation(act)
                for lr, act in acts.items()
                if isinstance(act, str)
            }
        )

    # old format - correlations
    corrs = reg.pop(_CORRELATION_KEY, None) or _DEFAULT_ACTIONS
    # check if this is old file format (values are strings); ignore other
    # types
    if isinstance(next(iter(corrs.values())), str):
        for lr, act in corrs.items():
            _REGISTER.correlations[lr].update_permanent_action(act)

    # rest in `reg` are mnemonics
    _REGISTER.mnemonics.update(reg)


def load() -> None:
    """Load learning database."""
    if (filepath := config.get_config_file(_MNEMONICS_FILENAME)) and (
        reg := Learning.unpickle_register(filepath)
    ):
        mns = reg.get(_MNEMONICS_KEY)
        if mns:
            # mnemonics are default dict
            assert isinstance(mns, defaultdict)
            _REGISTER.mnemonics = mns

        corrs = reg.get(_CORRELATION2_KEY)
        if corrs:
            assert isinstance(corrs, defaultdict)
            _REGISTER.correlations = corrs

        if mns or corrs or not reg:
            # we get mnemonics and correlations in new format so we finish
            return

        # old file format - upgrade
        pretty.print_info(__name__, "upgrading learning registry")
        _upgrade_and_fill_register(reg)

    else:
        # load defaults
        for leaf, act in _DEFAULT_ACTIONS.items():
            _REGISTER.correlations[leaf].update_permanent_action(act)


def save() -> None:
    """Save the learning record."""

    if not _REGISTER:
        pretty.print_debug(__name__, "Not writing empty register")
        return

    _REGISTER.prune()

    filepath = config.save_config_file(_MNEMONICS_FILENAME)
    assert filepath

    reg: dict[str, ty.Any] = {
        _MNEMONICS_KEY: _REGISTER.mnemonics,
        _CORRELATION2_KEY: _REGISTER.correlations,
    }
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
