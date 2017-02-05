# -*- coding: UTF-8 -*-

from kupfer.core import learn, relevance

def make_rankables(itr, rank=0):
    return (Rankable(str(obj), obj, rank) for obj in itr)

def wrap_rankable(obj, rank=0):
    return Rankable(str(obj), obj, rank)

class Rankable (object):
    """
    Rankable has an object (represented item),
    value (determines rank) and an associated rank

    Rankable has __hash__ and __eq__ of the object so that a Rankable's
    rank doesn't matter, Rankables can still be equal
    """
    # To save memory with (really) many Rankables
    __slots__ = ("rank", "value", "object", "aliases")
    def __init__(self, value, obj, rank=0):
        self.rank = rank
        self.value = value
        self.object = obj
        self.aliases = getattr(obj, "name_aliases", ())
    
    def __hash__(self):
        return hash(self.object)

    def __eq__(self, other):
        return (self.object == self.object)

    def __str__(self):
        return "%s: %s" % (self.rank, self.value)

    def __repr__(self):
        return "<Rankable %s repres %s at %x>" % (str(self), repr(self.object), id(self))

def bonus_objects(rankables, key):
    """generator of @rankables that have mnemonics for @key

    rank is added to prev rank, all items are yielded"""
    key = key.lower()
    get_record_score = learn.get_record_score
    for obj in rankables:
        obj.rank += get_record_score(obj.object, key)
        obj.rank += obj.object.rank_adjust
        yield obj

def add_rank_objects(rankables, rank):
    for obj in rankables:
        obj.rank += rank
        yield obj

def score_objects(rankables, key):
    """Return @rankables that pass with a >0 rank for @key,

    rank is added to previous rank,
    if not @key, then all items are returned"""
    _score = relevance.score
    key = key.lower()
    for rb in rankables:
        # Rank object
        rank = _score(rb.value, key)*100
        if rank < 90:
            for alias in rb.aliases:
                # consider aliases and change rb.value if alias is better
                # aliases rank lower so that value is chosen when close
                arank = _score(alias, key)*95
                if arank > rank:
                    rank = arank
                    rb.value = alias
        if rank:
            rb.rank = rank
            yield rb


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

