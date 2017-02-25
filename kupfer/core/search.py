# -*- coding: UTF-8 -*-

import operator
import itertools
from kupfer.core import learn, relevance

def make_rankables(itr, rank=0):
    return [Rankable(str(obj), obj, rank) for obj in itr]

def wrap_rankable(obj, rank=0):
    return Rankable(str(obj), obj, rank)

class Rankable (object):
    """
    Rankable has an object (represented item),
    value (determines rank) and an associated rank
    """
    # To save memory with (really) many Rankables
    __slots__ = ("rank", "value", "object", "aliases")
    def __init__(self, value, obj, rank=0):
        self.rank = rank
        self.value = value
        self.object = obj
        self.aliases = getattr(obj, "name_aliases", ())
    
    def __str__(self):
        return "%.2f: %r, %r" % (self.rank, self.value, self.object)

    def __repr__(self):
        return "<Rankable %s repres %r at %x>" % (self, self.object, id(self))

def bonus_objects(rankables, key):
    """
    rankables: List[Rankable]
    inncrement each for mnemonic score for key.
    """
    key = key.lower()
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key)

def bonus_actions(rankables, key):
    """
    generator of @rankables that have mnemonics for @key

    Add bonus for mnemonics and rank_adjust

    rank is added to prev rank, all items are yielded"""
    key = key.lower()
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key)
        obj.rank += obj.object.rank_adjust
        yield obj

def add_rank_objects(rankables, rank):
    """
    rankables: List[Rankable]
    rank: Fixed rank
    """
    for obj in rankables:
        obj.rank += rank

def _score_for_key(query):
    if len(query) == 1:
        return relevance.score_single
    else:
        return relevance.score

def score_objects(rankables, key):
    """
    rankables: List[Rankable]

    Prune rankables that score low for the key.
    """
    key = key.lower()
    _score = _score_for_key(key)
    for rb in rankables:
        # Rank object
        rb.rank = _score(rb.value, key) * 100
    for rb in rankables:
        if rb.rank < 90:
            rank = rb.rank
            for alias in rb.aliases:
                # consider aliases and change rb.value if alias is better
                # aliases rank lower so that value is chosen when close
                arank = _score(alias, key) * 95
                if arank > rank:
                    rank = arank
                    rb.value = alias
            rb.rank = rank
    rankables[:] = [rb for rb in rankables if rb.rank > 10]

def score_actions(rankables, for_leaf):
    """Alternative (rigid) scoring mechanism for objects,
    putting much more weight in rank_adjust
    """
    get_record_score = learn.get_record_score
    for obj in rankables:
        ra = obj.object.rank_adjust
        ra += learn.get_correlation_bonus(obj.object, for_leaf)
        if ra > 0:
            obj.rank = 50 + ra + get_record_score(obj.object)//2
        elif ra == 0:
            obj.rank = get_record_score(obj.object)
        else:
            obj.rank = -50 + ra + get_record_score(obj.object)
        yield obj


def _max_multiple(iterables, key):
    maxval = None
    for iterable in iterables:
        try:
            new_max = max(iterable, key=key)
        except ValueError:
            continue
        if maxval is None:
            maxval = new_max
        else:
            maxval = max(maxval, new_max, key=key)
    return maxval

def find_best_sort(rankables):
    """
    rankables: List[List[Rankable]]

    A special kind of lazy sort:

    simply find the best ranked item and yield it first,
    then if needed continue by sorting the rest.

    Note: this will duplicate the best item.

    Yield rankables in best rank first order
    """

    key = operator.attrgetter("rank")
    maxval = _max_multiple(rankables, key)
    if maxval is None: return
    yield maxval

    yield from sorted(itertools.chain(*rankables), key=key, reverse=True)
