"""
Sources definition.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""

from __future__ import annotations

import typing as ty

from kupfer.obj.base import Leaf, Source
from kupfer.obj.objects import SourceLeaf
from kupfer.support import itertools

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__all__ = (
    "MultiSource",
    "SourcesSource",
)


class SourcesSource(Source):
    """A source whose items are SourceLeaves for @source"""

    def __init__(
        self,
        sources: ty.Collection[Source],
        name: str | None = None,
        use_reprs: bool = True,
    ) -> None:
        super().__init__(name or _("Catalog Index"))
        self.sources = sources
        self.use_reprs = use_reprs

    def get_items(self) -> ty.Iterable[Leaf]:
        """Ask each Source for a Leaf substitute, else yield a SourceLeaf"""
        if self.use_reprs:
            for src in self.sources:
                yield src.get_leaf_repr() or SourceLeaf(src)

            return

        yield from map(SourceLeaf, self.sources)

    def should_sort_lexically(self) -> bool:
        return True

    def get_description(self) -> str:
        return _("An index of all available sources")

    def get_icon_name(self) -> str:
        return "kupfer-catalog"


class MultiSource(Source):
    """A source whose items are the combined items of all @sources"""

    fallback_icon_name = "kupfer-catalog"

    def __init__(self, sources: ty.Collection[Source]) -> None:
        super().__init__(_("Catalog"))
        self.sources = sources

    def is_dynamic(self) -> bool:
        """MultiSource should be dynamic so some of its content also can be."""
        return True

    def get_items(self) -> ty.Iterable[Leaf]:
        uniq_srcs = itertools.unique_iterator(
            S.toplevel_source() for S in self.sources
        )
        for src in uniq_srcs:
            yield from src.get_leaves() or ()

    def get_description(self) -> str:
        return _("Root catalog")
