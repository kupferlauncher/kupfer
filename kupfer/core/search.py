from __future__ import annotations

import itertools
import operator
import typing as ty

from kupfer.obj.base import KupferObject, Leaf

from . import learn, relevance


def make_rankables(
    itr: ty.Iterable[KupferObject], rank: int = 0
) -> ty.Iterator[Rankable]:
    """Create Rankable from some KupferObject:w"""
    return (Rankable(str(obj), obj, rank) for obj in itr)


def wrap_rankable(obj: ty.Any, rank: int = 0) -> Rankable:
    return Rankable(str(obj), obj, rank)


class Rankable:
    """
    Rankable has an object (represented item),
    value (determines rank) and an associated rank
    """

    # To save memory with (really) many Rankables
    __slots__ = ("rank", "value", "object", "aliases")

    def __init__(self, value: str, obj: KupferObject, rank: float = 0) -> None:
        self.rank = rank
        self.value: str = value
        self.object = obj
        self.aliases = getattr(obj, "name_aliases", ())

    def __str__(self):
        return f"{self.rank:.2f}: {self.value!r}, {self.object!r}"

    def __repr__(self):
        return f"<Rankable {self} repres {self.object!r} at {id(self):x}>"


def bonus_objects(
    rankables: ty.Iterable[Rankable], key: str
) -> ty.Iterator[Rankable]:
    """
    rankables: List[Rankable]
    inncrement each for mnemonic score for key.
    """
    key = key.lower()
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key)
        yield obj


def bonus_actions(
    rankables: ty.Iterable[Rankable], key: str
) -> ty.Iterator[Rankable]:
    """
    generator of @rankables that have mnemonics for @key

    Add bonus for mnemonics and rank_adjust

    rank is added to prev rank, all items are yielded"""
    key = key.lower()
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key) + obj.object.rank_adjust
        yield obj


def add_rank_objects(
    rankables: ty.Iterable[Rankable], rank: float
) -> ty.Iterator[Rankable]:
    """
    Add @rank to rank of all @rankables.

    rankables: Iterable[Rankable] - updated
    rank: Fixed rank
    """
    for obj in rankables:
        obj.rank += rank
        yield obj


def _score_for_key(query: str) -> ty.Callable[[str, str], float]:
    if len(query) == 1:
        return relevance.score_single

    return relevance.score


def score_objects(
    rankables: ty.Iterable[Rankable], key: str
) -> ty.Iterator[Rankable]:
    """
    rankables: List[Rankable]

    Prune rankables that score low for the key.

    TODO: convert to generator
    """
    key = key.lower()
    _score = _score_for_key(key)
    for rankable in rankables:
        # Rank object
        rank = rankable.rank = _score(rankable.value, key) * 100
        if rank < 90:
            for alias in rankable.aliases:
                # consider aliases and change rb.value if alias is better
                # aliases rank lower so that value is chosen when close
                if (arank := _score(alias, key) * 95) > rank:
                    rank = arank
                    rankable.value = alias

            rankable.rank = rank

        if rankable.rank > 10:
            yield rankable


def score_actions(
    rankables: ty.Iterable[Rankable], for_leaf: ty.Optional[Leaf]
) -> ty.Iterator[Rankable]:
    """Alternative (rigid) scoring mechanism for objects,
    putting much more weight in rank_adjust
    """
    get_record_score = learn.get_record_score
    for obj in rankables:
        rank_adj = obj.object.rank_adjust
        rank_adj += learn.get_correlation_bonus(obj.object, for_leaf)

        if rank_adj > 0:
            obj.rank = 50 + rank_adj + get_record_score(obj.object) // 2
        elif rank_adj == 0:
            obj.rank = get_record_score(obj.object)
        else:
            obj.rank = -50 + rank_adj + get_record_score(obj.object)

        yield obj


# K: not in use
# def _max_multiple(iterables, key):
#     maxval = None
#     for iterable in iterables:
#         try:
#             new_max = max(iterable, key=key)
#         except ValueError:
#             continue

#         if maxval is None:
#             maxval = new_max
#         else:
#             maxval = max(maxval, new_max, key=key)

#     return maxval


def find_best_sort(
    rankables: list[list[Rankable]],
) -> ty.Iterator[Rankable]:
    """
    rankables: List[List[Rankable]]

    A special kind of lazy sort:

    simply find the best ranked item and yield it first,
    then if needed continue by sorting the rest.

    Note: this will duplicate the best item.

    Yield rankables in best rank first order
    """

    key = operator.attrgetter("rank")
    # maxval = _max_multiple(rankables, key)
    maxval = max(itertools.chain(*rankables), default=None, key=key)
    if maxval is None:
        return

    yield maxval
    yield from sorted(itertools.chain(*rankables), key=key, reverse=True)
