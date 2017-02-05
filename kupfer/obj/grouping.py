# -*- encoding: UTF-8 -*-
"""
Classes used to provide grouping leaves mechanism.
"""
import copy
import itertools
import time
import weakref

from kupfer.objects import Leaf, Source
from kupfer import utils

__author__ = ("Karol Będkowski <karol.bedkowsk+gh@gmail.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>" )

class GroupingLeaf (Leaf):
    """
    A Leaf that groups with other leaves inside Grouping Sources

    The represented object of a GroupedLeaf is a dictionary of (slot, value)
    pairs, where slot identifies the slot, and the value is something that must
    be equal to be grouped.

    The GroupingLeaf must have a value for all @grouping_slots, but values of
    None will not be grouped with others.
    """
    grouping_slots = ()

    def __init__(self, obj, name):
        Leaf.__init__(self, obj, name)
        self.links = [self]

    def slots(self):
        return self.object

    def has_content(self):
        return len(self.links) > 1

    def content_source(self, alternate=False):
        return _GroupedItemsSource(self)

    def __len__(self):
        return len(self.links)

    def __contains__(self, key):
        "Return True if GroupedLeaf has value for @key"
        return any(key in leaf.object for leaf in self.links)

    def __getitem__(self, key):
        "Get first (canonical) value for key"
        try:
            return next(iter(self.all(key)))
        except StopIteration:
            raise KeyError("%s has no slot %s" % (self, key))

    def all(self, key):
        "Return iterator of all values for @key"
        return (leaf.object[key] for leaf in self.links if key in leaf.object)

    def check_key(self, key):
        ''' check if GroupedLeaf has non empty value for @key '''
        return any(bool(leaf.object.get(key)) for leaf in self.links)

class GroupingSource (Source):

    def __init__(self, name, sources):
        Source.__init__(self, name)
        self.sources = sources

    def get_leaves(self, force_update=False):
        starttime = time.time()
        # map (slot, value) -> group
        groups = {}
        non_group_leaves = []
        for src in self.sources:
            leaves = Source.get_leaves(src, force_update)
            for leaf in leaves:
                try:
                    slots = leaf.slots()
                except AttributeError:
                    # Let through Non-grouping leaves
                    non_group_leaves.append(leaf)
                    continue
                slots = leaf.slots()
                for slot in leaf.grouping_slots:
                    value = slots.get(slot)
                    if value:
                        groups.setdefault((slot, value), set()).add(leaf)
                if not leaf.grouping_slots:
                    self.output_error("GroupingLeaf has no grouping slots",
                            repr(leaf))

        # Keep track of keys that are only duplicate references
        redundant_keys = set()

        def merge_groups(key1, key2):
            if groups[key1] is groups[key2]:
                return
            groups[key1].update(groups[key2])
            groups[key2] = groups[key1]
            redundant_keys.add(key2)

        # Find all (slot, value) combinations that have more than one leaf
        # and merge those groups
        for (slot, value), leaves in groups.items():
            if len(leaves) <= 1:
                continue
            for leaf in list(leaves):
                for slot2 in leaf.grouping_slots:
                    for value2 in leaf.all(slot2):
                        if not value2:
                            continue
                        merge_groups((slot, value), (slot2, value2))
        if self.should_sort_lexically():
            sort_func = utils.locale_sort
        else:
            sort_func = lambda x: x

        keys = set(groups)
        keys.difference_update(redundant_keys)
        leaves = sort_func(self._make_group_leader(groups[K]) for K in keys)
        mergetime = time.time() - starttime
        if mergetime > 0.05:
            self.output_debug("Warning(?): merged in %s seconds" % mergetime)
        return itertools.chain(non_group_leaves, leaves)

    def repr_key(self):
        # Distinguish when used as GroupingSource
        if type(self) is GroupingSource:
            return str(self)
        return Source.repr_key(self)

    @classmethod
    def _make_group_leader(cls, leaves):
        if len(leaves) == 1:
            (leaf, ) = leaves
            return leaf
        obj = copy.copy(next(iter(leaves)))
        obj.links = list(leaves)
        for other in leaves:
            obj.kupfer_add_alias(str(other))
            # adding the other's aliases can be misleading
            # since the matched email address might not be
            # what we are e-mailing
            # obj.name_aliases.update(other.name_aliases)
        return obj

class ToplevelGroupingSource (GroupingSource):
    """
    Sources of this type group their leaves with others in the toplevel
    of the catalog.
    """
    _sources = {}

    def __init__(self, name, category):
        GroupingSource.__init__(self, name, [self])
        self.category = category

    def toplevel_source(self):
        if self.category not in self._sources:
            return self
        sources = list(self._sources[self.category].keys())
        return GroupingSource(self.category, sources)

    def initialize(self):
        if not self.category in self._sources:
            self._sources[self.category] = weakref.WeakKeyDictionary()
        self._sources[self.category][self] = 1
        self.output_debug("Register %s source %s" % (self.category, self))

    def finalize(self):
        del self._sources[self.category][self]
        self.output_debug("Unregister %s source %s" % (self.category, self))

class _GroupedItemsSource(Source):
    def __init__(self, leaf):
        Source.__init__(self, str(leaf))
        self._leaf = leaf

    def get_items(self):
        for leaf in self._leaf.links:
            yield leaf

    def repr_key(self):
        return repr(self._leaf)



