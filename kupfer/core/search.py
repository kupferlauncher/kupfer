from __future__ import annotations

import itertools
import operator
import typing as ty

from kupfer.core import learn, relevance
from kupfer.obj.base import Action, Leaf

__all__ = (
    "Rankable",
    "add_bonus_to_objects",
    "add_bonus_to_action",
    "add_rank_to_objects",
    "find_best_sort",
    "make_rankables",
    "score_actions",
    "score_objects",
    "wrap_rankable",
)

# RankableObject is type of object that can be put in Rankable.
RankableObject = ty.Union[Leaf, Action]


def make_rankables(
    itr: ty.Iterable[RankableObject], rank: int = 0
) -> ty.Iterable[Rankable]:
    """Create Rankable from some KupferObject:w"""
    return (Rankable(str(obj), obj, rank) for obj in itr)


def wrap_rankable(obj: Leaf, rank: int = 0) -> Rankable:
    return Rankable(str(obj), obj, rank)


class Rankable:
    """Rankable has an object (represented item), value (determines rank)
    and an associated rank."""

    # To save memory with (really) many Rankables
    __slots__ = ("aliases", "object", "rank", "value")

    def __init__(self, value: str, obj: RankableObject, rank: int = 0) -> None:
        self.rank: int = rank
        self.value: str = value
        self.object: RankableObject = obj
        self.aliases: ty.Collection[str] = getattr(obj, "name_aliases", ())

    def __str__(self):
        return f"{self.rank:.2f}: {self.value!r}, {self.object!r}"

    def __repr__(self):
        return f"<Rankable {self} repres {self.object!r} at {id(self):x}>"


def add_bonus_to_objects(
    rankables: ty.Iterable[Rankable], key: str, extra_bonus: int = 0
) -> ty.Iterator[Rankable]:
    """
    Increment rank of each item in `rankables` for mnemonic score for key and
    `extra_bonus`.
    """
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key) + extra_bonus
        yield obj


def add_bonus_to_action(
    rankables: ty.Iterable[Rankable], key: str
) -> ty.Iterator[Rankable]:
    """
    generator of @rankables that have mnemonics for @key

    Add bonus for mnemonics and rank_adjust

    rank is added to prev rank, all items are yielded"""
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key) + obj.object.rank_adjust
        yield obj


def add_rank_to_objects(
    rankables: ty.Iterable[Rankable], rank: int
) -> ty.Iterator[Rankable]:
    """
    Add @rank to rank of all @rankables.

    rankables: Iterable[Rankable] - updated
    rank: Fixed rank
    """
    for obj in rankables:
        obj.rank += rank
        yield obj


def score_objects(
    rankables: ty.Iterable[Rankable], key: str
) -> ty.Iterator[Rankable]:
    """
    rankables: List[Rankable]

    Prune rankables that score low for the key.
    """
    key = key.lower()
    _score = relevance.score_single if len(key) == 1 else relevance.score

    for rankable in rankables:
        # Rank object
        rank = int(_score(rankable.value, key) * 100)
        if rank < 90:  # noqa:PLR2004
            # consider aliases and change rb.value if alias is better
            # aliases rank lower so that value is chosen when close
            arank_value = max(
                ((_score(alias, key), alias) for alias in rankable.aliases),
                default=None,
            )
            if arank_value:
                arank, value = arank_value
                arank *= 95
                if arank > rank:
                    rankable.value = value
                    rank = int(arank)

        rankable.rank = rank

        if rankable.rank > 10:  # noqa:PLR2004
            yield rankable


def score_actions(
    rankables: ty.Iterable[Rankable], for_leaf: Leaf | None
) -> ty.Iterator[Rankable]:
    """Alternative (rigid) scoring mechanism for objects,
    putting much more weight in rank_adjust."""
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj_object = ty.cast("Action", obj.object)
        rank_adj = obj_object.rank_adjust + learn.get_correlation_bonus(
            obj_object, for_leaf
        )

        if rank_adj > 0:
            obj.rank = 50 + rank_adj + get_record_score(obj_object) // 2
        elif rank_adj == 0:
            obj.rank = get_record_score(obj_object)
        else:
            obj.rank = -50 + rank_adj + get_record_score(obj_object)

        yield obj


_rank_key = operator.attrgetter("rank")


def find_best_sort(
    rankables: ty.Iterable[Rankable],
) -> ty.Iterable[Rankable]:
    """Yield rankables in best rank first order.
    A special kind of lazy sort: simply find the best ranked item and yield
    it first, then if needed continue by sorting the rest.

    Note: this will duplicate the best item."""
    r1, r2 = itertools.tee(rankables, 2)
    maxval = max(r1, default=None, key=_rank_key)
    if maxval is None:
        return

    yield maxval
    yield from sorted(r2, key=_rank_key, reverse=True)
