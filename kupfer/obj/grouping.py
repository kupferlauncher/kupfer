"""
Classes used to provide grouping leaves mechanism.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import copy
import itertools
import time
import typing as ty
import weakref
from collections import defaultdict

from gi.repository import Gtk, Gdk

from kupfer.support import kupferstring, itertools as kitertools
from kupfer.obj.base import Leaf, Source, Action
from kupfer.core import commandexec

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__author__ = (
    "Karol Będkowski <karol.bedkowsk+gh@gmail.com>, "
    "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"
)


__all__ = (
    "GroupingLeaf",
    "GroupingSource",
    "ToplevelGroupingSource",
)

Slots = ty.Optional[dict[str, ty.Any]]


class GroupingLeaf(Leaf):
    """A Leaf that groups with other leaves inside Grouping Sources.

    The represented object of a GroupedLeaf is a dictionary of (slot, value)
    pairs, where slot identifies the slot, and the value is something that must
    be equal to be grouped.

    The GroupingLeaf must have a value for all @grouping_slots, but values of
    None will not be grouped with others.
    """

    grouping_slots: tuple[str, ...] = ()

    def __init__(self, obj: ty.Any, name: str) -> None:
        Leaf.__init__(self, obj, name)
        self.links = [self]

    def slots(self) -> Slots:
        return ty.cast(Slots, self.object)

    def has_content(self) -> bool:
        return len(self.links) > 1

    def content_source(self, alternate: bool = False) -> Source:
        return _GroupedItemsSource(self)

    def __len__(self) -> int:
        return len(self.links)

    def __contains__(self, key: ty.Any) -> bool:
        "Return True if GroupedLeaf has value for @key"
        return any(key in leaf.object for leaf in self.links)

    def __getitem__(self, key: ty.Any) -> ty.Any:
        "Get first (canonical) value for key"
        try:
            return next(self.all(key))
        except StopIteration as exc:
            raise KeyError(f"{self} has no slot {key}") from exc

    def all(self, key: ty.Any) -> ty.Iterator[ty.Any]:
        "Return iterator of all values for @key"
        return (leaf.object[key] for leaf in self.links if key in leaf.object)

    def check_key(self, key: ty.Any) -> bool:
        """check if GroupedLeaf has non empty value for @key"""
        return any(bool(leaf.object.get(key)) for leaf in self.links)

    def get_actions(self) -> ty.Iterable[Action]:
        for key, val in kitertools.unique_iterator(
            keyval for leaf in self.links for keyval in leaf.object.items()
        ):
            yield CopySlotAction(key, val)


_Groups = dict[tuple[str, ty.Any], set[GroupingLeaf]]
_NonGroupLeaves = list[Leaf]


class GroupingSource(Source):
    def __init__(self, name: str, sources: list[Source]) -> None:
        Source.__init__(self, name)
        self.sources = sources

    def _get_groups(
        self, force_update: bool
    ) -> tuple[_Groups, _NonGroupLeaves]:
        groups: _Groups = defaultdict(set)
        non_group_leaves: list[Leaf] = []

        for src in self.sources:
            leaves = Source.get_leaves(src, force_update)
            for leaf in leaves or ():
                try:
                    slots = leaf.slots()  # type: ignore
                except AttributeError:
                    # Let through Non-grouping leaves
                    non_group_leaves.append(leaf)
                else:
                    assert isinstance(leaf, GroupingLeaf)

                    if not leaf.grouping_slots:
                        self.output_error(
                            "GroupingLeaf has no grouping slots", repr(leaf)
                        )
                        continue

                    for slot in leaf.grouping_slots:
                        if value := slots.get(slot):
                            groups[(slot, value)].add(leaf)

        return groups, non_group_leaves

    def _merge_groups(self, groups: _Groups) -> set[tuple[str, ty.Any]]:
        redundant_keys = set()

        def merge_groups(key1, key2):
            if groups[key1] is not groups[key2]:
                groups[key1].update(groups[key2])
                groups[key2] = groups[key1]
                redundant_keys.add(key2)

        # Find all (slot, value) combinations that have more than one leaf
        # and merge those groups
        for (slot, value), gleaves in groups.items():
            if len(gleaves) <= 1:
                continue

            for leaf in list(gleaves):
                for slot2 in leaf.grouping_slots:
                    for value2 in leaf.all(slot2):
                        if value2:
                            merge_groups((slot, value), (slot2, value2))

        return redundant_keys

    def get_leaves(self, force_update: bool = False) -> ty.Iterable[Leaf]:
        starttime = time.time()
        # map (slot, value) -> group
        groups, non_group_leaves = self._get_groups(force_update)

        # Keep track of keys that are only duplicate references
        redundant_keys = self._merge_groups(groups)

        keys = set(groups)
        keys.difference_update(redundant_keys)

        leaves: ty.Iterable[Leaf] = (
            self._make_group_leader(groups[K]) for K in keys
        )
        if self.should_sort_lexically():
            leaves = kupferstring.locale_sort(leaves)

        if (mergetime := time.time() - starttime) > 0.05:
            self.output_debug(f"Warning(?): merged in {mergetime} seconds")

        return itertools.chain(non_group_leaves, leaves)

    def repr_key(self) -> ty.Any:
        # Distinguish when used as GroupingSource
        if isinstance(self, GroupingSource):
            return str(self)

        return Source.repr_key(self)

    @classmethod
    def _make_group_leader(cls, leaves: set[GroupingLeaf]) -> Leaf:
        if len(leaves) == 1:
            (leaf,) = leaves
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


class ToplevelGroupingSource(GroupingSource):
    """Sources of this type group their leaves with others in the toplevel
    of the catalog."""

    _sources: dict[str, weakref.WeakKeyDictionary[Source, int]] = {}

    def __init__(self, name: str, category: str) -> None:
        GroupingSource.__init__(self, name, [self])
        self.category = category

    def toplevel_source(self) -> Source:
        if self.category not in self._sources:
            return self

        sources = list(self._sources[self.category].keys())
        return GroupingSource(self.category, sources)

    def initialize(self) -> None:
        if self.category not in self._sources:
            self._sources[self.category] = weakref.WeakKeyDictionary()

        self._sources[self.category][self] = 1
        self.output_debug(f"Register {self.category} source {self}")

    def finalize(self) -> None:
        del self._sources[self.category][self]
        self.output_debug(f"Unregister {self.category} source {self}")


class _GroupedItemsSource(Source):
    def __init__(self, leaf: GroupingLeaf) -> None:
        Source.__init__(self, str(leaf))
        self._leaf = leaf

    def get_items(self) -> ty.Iterator[Leaf]:
        yield from self._leaf.links

    def repr_key(self) -> ty.Any:
        return repr(self._leaf)


class CopySlotAction(Action):
    rank_adjust = -5

    """Action for GroupingLeaf - copy given slot value to clipboard."""

    def __init__(self, slot_name: str, value: str) -> None:
        name = slot_name.replace("_", " ").lower()
        super().__init__(_("Copy %s") % name)
        self.value = value

    def wants_context(self):
        return True

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert ctx
        clip = Gtk.Clipboard.get_for_display(
            ctx.environment.get_screen().get_display(), Gdk.SELECTION_CLIPBOARD
        )
        clip.set_text(self.value, -1)
        return None

    def get_description(self) -> str:
        return _("Copy '%s' to clipboard") % self.value
