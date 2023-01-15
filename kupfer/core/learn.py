from __future__ import annotations

import os
import pickle
import random
import typing as ty
from pathlib import Path

from kupfer import config
from kupfer.obj.base import KupferObject, Leaf
from kupfer.support import conspickle, pretty

_MNEMONICS_FILENAME = "mnemonics.pickle"
_CORRELATION_KEY = "kupfer.bonus.correlation"

## this is a harmless default
_DEFAULT_ACTIONS = {
    "<builtin.AppLeaf gnome-terminal>": "<builtin.LaunchAgain>",
    "<builtin.AppLeaf xfce4-terminal>": "<builtin.LaunchAgain>",
}

_FAVORITES: ty.Set[str] = set()


class Mnemonics:
    """
    Class to describe a collection of mnemonics
    as well as the total count
    """

    def __init__(self) -> None:
        self.mnemonics: ty.Dict[str, int] = {}
        self.count: int = 0

    def __repr__(self) -> str:
        mnm = "".join(f"{m}: {c}, " for m, c in self.mnemonics.items())
        return f"<{self.__class__.__name__} {self.count} {mnm}>"

    def increment(self, mnemonic: ty.Optional[str] = None) -> None:
        if mnemonic:
            mcount = self.mnemonics.get(mnemonic, 0)
            self.mnemonics[mnemonic] = mcount + 1

        self.count += 1

    def decrement(self) -> None:
        """Decrement total count and the least mnemonic"""
        if self.mnemonics:
            key = min(self.mnemonics, key=lambda k: self.mnemonics[k])
            if (mcount := self.mnemonics[key]) > 1:
                self.mnemonics[key] = mcount - 1
            else:
                del self.mnemonics[key]

        self.count = max(self.count - 1, 0)

    def __bool__(self) -> bool:
        return self.count > 0


class Learning:
    @classmethod
    def unpickle_register(
        cls, pickle_file: str
    ) -> ty.Optional[ty.Dict[str, ty.Any]]:
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
    def pickle_register(
        cls, reg: ty.Dict[str, ty.Any], pickle_file: str
    ) -> bool:
        ## Write to tmp then rename over for atomicity
        tmp_pickle_file = f"{pickle_file}.{os.getpid()}"
        pretty.print_debug(__name__, f"Saving to {pickle_file}")
        Path(tmp_pickle_file).write_bytes(
            pickle.dumps(reg, pickle.HIGHEST_PROTOCOL)
        )
        os.rename(tmp_pickle_file, pickle_file)
        return True


# under _CORRELATION_KEY is {str:str}, other keys keeps Mnemonics
_REGISTER: ty.Dict[str, ty.Union[Mnemonics, ty.Dict[str, str]]] = {}


def record_search_hit(obj: ty.Any, key: str | None = None) -> None:
    """
    Record that KupferObject @obj was used, with the optional
    search term @key recording
    """
    name = repr(obj)
    mns = _REGISTER.get(name)
    if not mns:
        mns = _REGISTER[name] = Mnemonics()

    assert isinstance(mns, Mnemonics)
    mns.increment(key or "")


def get_record_score(obj: ty.Any, key: str = "") -> float:
    """
    Get total score for KupferObject @obj,
    bonus score is given for @key matches
    """
    name = repr(obj)
    fav = 7 * (name in _FAVORITES)
    if name not in _REGISTER:
        return fav

    mns = _REGISTER[name]
    assert isinstance(mns, Mnemonics)
    if not key:
        return fav + 50 * (1 - 1.0 / (mns.count + 1))

    stats = mns.mnemonics
    closescr = sum(stats[m] for m in stats if m.startswith(key))
    mnscore = 30 * (1 - 1.0 / (closescr + 1))
    exact = stats.get(key, 0)
    mnscore += 50 * (1 - 1.0 / (exact + 1))
    return fav + mnscore


def get_correlation_bonus(obj: KupferObject, for_leaf: Leaf | None) -> int:
    """
    Get the bonus rank for @obj when used with @for_leaf
    """
    rval = _REGISTER[_CORRELATION_KEY]
    assert isinstance(rval, dict)
    if rval.get(repr(for_leaf)) == repr(obj):
        return 50

    return 0


def set_correlation(obj: Leaf, for_leaf: Leaf) -> None:
    """
    Register @obj to get a bonus when used with @for_leaf
    """
    rval = _REGISTER[_CORRELATION_KEY]
    assert isinstance(rval, dict)
    rval[repr(for_leaf)] = repr(obj)


def _get_mnemonic_items(
    in_register: ty.Dict[str, ty.Any]
) -> ty.List[ty.Tuple[str, ty.Any]]:
    return [(k, v) for k, v in in_register.items() if k != _CORRELATION_KEY]


def get_object_has_affinity(obj: Leaf) -> bool:
    """
    Return if @obj has any positive score in the register
    """
    robj = repr(obj)
    return bool(
        _REGISTER.get(robj)
        or _REGISTER[_CORRELATION_KEY].get(robj)  # type: ignore
    )


def erase_object_affinity(obj: Leaf) -> None:
    """
    Remove all track of affinity for @obj
    """
    robj = repr(obj)
    _REGISTER.pop(robj, None)
    _REGISTER[_CORRELATION_KEY].pop(robj, None)  # type: ignore


def _prune_register() -> None:
    """
    Remove items with chance (len/25000)

    Assuming homogenous records (all with score one) we keep:
    x_n+1 := x_n * (1 - chance)

    To this we have to add the expected number of added mnemonics per
    invocation, est. 10, and we can estimate a target number of saved mnemonics.
    """
    random.seed()
    rand = random.random

    goalitems = 500
    flux = 2.0
    alpha = flux / goalitems**2

    chance = min(0.1, len(_REGISTER) * alpha)
    for leaf, mne in _get_mnemonic_items(_REGISTER):
        if rand() <= chance:
            mne.decrement()
            if not mne:
                _REGISTER.pop(leaf)

    pretty.print_debug(
        __name__, f"Pruned register ({len(_REGISTER)} mnemonics)"
    )


def load() -> None:
    """
    Load learning database
    """
    _REGISTER.clear()

    if filepath := config.get_config_file(_MNEMONICS_FILENAME):
        if reg := Learning.unpickle_register(filepath):
            _REGISTER.update(reg)

    if _CORRELATION_KEY not in _REGISTER:
        _REGISTER[_CORRELATION_KEY] = _DEFAULT_ACTIONS


def save() -> None:
    """
    Save the learning record
    """
    if not _REGISTER:
        pretty.print_debug(__name__, "Not writing empty register")
        return

    if len(_REGISTER) > 100:
        _prune_register()

    filepath = config.save_config_file(_MNEMONICS_FILENAME)
    assert filepath
    Learning.pickle_register(_REGISTER, filepath)


def add_favorite(obj: KupferObject) -> None:
    _FAVORITES.add(repr(obj))


def remove_favorite(obj: KupferObject) -> None:
    _FAVORITES.discard(repr(obj))


def is_favorite(obj: KupferObject) -> bool:
    return repr(obj) in _FAVORITES


def unregister(obj):
    _REGISTER.pop(obj, None)
