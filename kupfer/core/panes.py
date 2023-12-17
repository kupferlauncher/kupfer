"""Pane objects definition.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import itertools
import typing as ty

from gi.repository import GObject

from kupfer.obj import objects
from kupfer.obj.base import Action, AnySource, KupferObject, Leaf, Source
from kupfer.support import pretty
from kupfer.core import actioncompat
from kupfer.core.search import Rankable
from kupfer.core.searcher import Searcher
from kupfer.core.sources import get_source_controller

__all__ = (
    "LeafPane",
    "Pane",
    "PrimaryActionPane",
    "SecondaryObjectPane",
    "SearchContext",
)

SearchContext = tuple[int, ty.Any]


def _dress_leaves(
    seq: ty.Iterable[Rankable], action: Action | None
) -> ty.Iterable[Rankable]:
    """yield items of @seq "dressed" by the source controller"""
    sctr = get_source_controller()
    decorate_object = sctr.decorate_object
    for itm in seq:
        decorate_object(itm.object, action=action)  # type:ignore
        yield itm


# Pane Object type definition
PO = ty.TypeVar("PO", bound=KupferObject)


class Pane(GObject.GObject, ty.Generic[PO]):  # type:ignore
    """Pane with `PO` type objects.

    signals:
        search-result (match, match_iter, context)
    """

    __gtype_name__ = "Pane"

    def __init__(self):
        super().__init__()
        self._selection: PO | None = None
        self._latest_key: str | None = None
        self.outstanding_search: int = -1
        self.outstanding_search_id: int = -1
        self._searcher = Searcher()

    def select(self, item: PO | None) -> None:
        self._selection = item

    def get_selection(self) -> PO | None:
        return self._selection

    def reset(self) -> None:
        self._selection = None
        self._latest_key = None

    def get_latest_key(self) -> str | None:
        return self._latest_key

    def get_can_enter_text_mode(self) -> bool:
        return False

    def get_should_enter_text_mode(self) -> bool:
        return False

    def emit_search_result(
        self,
        match: Rankable | None,
        match_iter: ty.Iterable[Rankable],
        context: SearchContext | None,
    ) -> None:
        self.emit("search-result", match, match_iter, context)


GObject.signal_new(
    "search-result",
    Pane,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT),
)


class LeafPane(Pane[Leaf], pretty.OutputMixin):
    __gtype_name__ = "LeafPane"

    def __init__(self):
        super().__init__()
        # source_stack keep track on history selected sources and leaves
        self._source_stack: list[tuple[AnySource, Leaf | None]] = []
        self._source: AnySource | None = None
        self.object_stack: list[Leaf] = []

    def select(self, item: Leaf | None) -> None:
        assert item is None or isinstance(
            item, Leaf
        ), "New selection for object pane is not a Leaf!"
        super().select(item)

    def _load_source(self, src: AnySource) -> AnySource:
        """Try to get a source from the SourceController,
        if it is already loaded we get it from there, else
        returns @src"""
        sctr = get_source_controller()
        return sctr.get_canonical_source(src)

    def get_source(self) -> AnySource | None:
        return self._source

    def source_rebase(self, src: AnySource) -> None:
        self._source_stack.clear()
        self._source = self._load_source(src)
        self.refresh_data()

    def push_source(self, src: AnySource) -> None:
        if self._source:
            self._source_stack.append((self._source, self._selection))

        self._source = self._load_source(src)
        self.refresh_data()

    def _pop_source(self) -> bool:
        """Remove source from stack. Return True if succeeded"""
        if self._source_stack:
            self._source, self._selection = self._source_stack.pop()
            return True

        return False

    def is_at_source_root(self) -> bool:
        """Return True if we have no source stack"""
        return not self._source_stack

    def object_stack_push(self, obj: Leaf) -> None:
        self.object_stack.append(obj)

    def object_stack_pop(self) -> Leaf:
        return self.object_stack.pop()

    def get_can_enter_text_mode(self) -> bool:
        return self.is_at_source_root()

    def get_should_enter_text_mode(self) -> bool:
        return False

    def refresh_data(self, select: ty.Any = None) -> None:
        self.emit("new-source", self._source, select)

    def browse_up(self) -> bool:
        """Try to browse up to previous sources, from current source"""
        succ = self._pop_source()
        if not succ:
            assert self._source
            if self._source.has_parent():
                self.source_rebase(self._source.get_parent())  # type:ignore
                succ = True

        if succ:
            self.refresh_data(select=self._selection)

        return succ

    def browse_down(self, alternate: bool = False) -> bool:
        """Browse into @leaf if it's possible and save away the previous sources
        in the stack. If @alternate, use the Source's alternate method."""
        leaf: Leaf | None = self.get_selection()
        if leaf and leaf.has_content():
            if csrc := leaf.content_source(alternate=alternate):
                self.push_source(csrc)
                return True

        return False

    def reset(self) -> None:
        """Pop all sources and go back to top level"""
        Pane.reset(self)
        while self._pop_source():
            pass

        self.refresh_data()

    def soft_reset(self) -> AnySource | None:
        Pane.reset(self)
        while self._pop_source():
            pass

        return self._source

    def search(
        self,
        key: str = "",
        context: SearchContext | None = None,
        text_mode: bool = False,
    ) -> None:
        """Search for `key`"""

        self._latest_key = key
        sources_: ty.Iterable[AnySource] = ()
        if not text_mode:
            if srcs := self.get_source():
                sources_ = (srcs,)

        if key and self.is_at_source_root():
            # Only use text sources when we are at root catalog
            sctr = get_source_controller()
            textsrcs = sctr.get_text_sources()
            sources_ = itertools.chain(sources_, textsrcs)

        def _decorator(seq):
            return _dress_leaves(seq, action=None)

        match, match_iter = self._searcher.search(
            sources_, key, score=bool(key), decorator=_decorator
        )
        self.emit_search_result(match, match_iter, context)


GObject.signal_new(
    "new-source",
    LeafPane,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT),
)


class PrimaryActionPane(Pane[Action]):
    def __init__(self):
        super().__init__()
        self._action_valid_cache: dict[int, bool] = {}
        self.set_item(None)

    def select(self, item: Action | None) -> None:
        assert not item or isinstance(
            item, Action
        ), "Selection in action pane is not an Action!"
        super().select(item)

    def set_item(self, item: Leaf | None) -> None:
        """Set which @item we are currently listing actions for"""
        self._current_item = item
        self._action_valid_cache.clear()

    def search(
        self,
        key: str = "",
        context: SearchContext | None = None,
        text_mode: bool = False,
    ) -> None:
        """Search: Register the search method in the event loop using @key,
        promising to return @context in the notification about the result,
        having selected @item in PaneSel.SOURCE

        If we already have a call to search, we remove the "source"
        so that we always use the most recently requested search."""

        self._latest_key = key
        leaf = self._current_item
        if not leaf:
            self.emit_search_result(None, (), context)
            return

        if isinstance(leaf, objects.ActionLeaf):
            # for ActionLeaf get only actions defined in leaf (should be one,
            # ignore other actions).
            actions = leaf.get_actions()
            match, match_iter = self._searcher.rank_actions(actions, "", leaf)

        else:
            actions = actioncompat.actions_for_item(
                leaf, get_source_controller()
            )
            cache = self._action_valid_cache

            def valid_decorator(seq):
                """Check if actions are valid before access"""
                assert leaf

                for obj in seq:
                    action = obj.object
                    action_hash = hash(action)
                    valid = cache.get(action_hash)
                    if valid is None:
                        valid = actioncompat.action_valid_for_item(action, leaf)
                        cache[action_hash] = valid

                    if valid:
                        yield obj

            match, match_iter = self._searcher.rank_actions(
                actions, key, leaf, decorator=valid_decorator
            )

        self.emit_search_result(match, match_iter, context)


class SecondaryObjectPane(LeafPane):
    __gtype_name__ = "SecondaryObjectPane"

    def __init__(self):
        LeafPane.__init__(self)
        self._current_item: Leaf | None = None
        self._current_action: Action | None = None

    def reset(self) -> None:
        LeafPane.reset(self)
        self._searcher.reset()

    def set_item_and_action(
        self, item: Leaf | None, act: Action | None
    ) -> None:
        self._current_item = item
        self._current_action = act
        if item and act:
            ownsrc, use_catalog = actioncompat.iobject_source_for_action(
                act, item
            )
            if ownsrc and not use_catalog:
                self.source_rebase(ownsrc)
            else:
                extra_sources = (
                    ty.cast(list[Source], [ownsrc]) if ownsrc else None
                )

                sctr = get_source_controller()
                self.source_rebase(
                    sctr.root_for_types(act.object_types(), extra_sources)
                )
        else:
            self.reset()

    def get_can_enter_text_mode(self) -> bool:
        """Check if there are any reasonable text sources for this action"""
        assert self._current_action
        atroot = self.is_at_source_root()
        types = tuple(self._current_action.object_types())
        sctr = get_source_controller()
        textsrcs = sctr.get_text_sources()
        return atroot and any(
            sctr.good_source_for_types(s, types) for s in textsrcs
        )

    def get_should_enter_text_mode(self):
        return self.is_at_source_root() and hasattr(
            self.get_source(), "get_text_items"
        )

    def search(
        self,
        key: str = "",
        context: SearchContext | None = None,
        text_mode: bool = False,
    ) -> None:
        """
        filter for action @item
        """
        self._latest_key = key

        assert self._current_action
        if not self._current_item:
            self.emit_search_result(None, (), context)
            return

        sources_: ty.Iterable[AnySource] = []
        if not text_mode or hasattr(self.get_source(), "get_text_items"):
            if srcs := self.get_source():
                sources_ = itertools.chain(sources_, (srcs,))

        if key and self.is_at_source_root():
            # Only use text sources when we are at root catalog
            sctr = get_source_controller()
            if textsrcs := sctr.get_text_sources():
                sources_ = itertools.chain(sources_, textsrcs)

        item_check = actioncompat.iobjects_valid_for_action(
            self._current_action, self._current_item
        )

        def decorator(seq):
            return _dress_leaves(seq, action=self._current_action)

        match, match_iter = self._searcher.search(
            sources_,
            key,
            score=True,
            item_check=item_check,
            decorator=decorator,
        )
        self.emit_search_result(match, match_iter, context)
