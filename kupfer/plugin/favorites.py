from __future__ import annotations

__kupfer_name__ = _("Favorites")
__kupfer_sources__ = ("FavoritesSource",)
__kupfer_actions__ = ("AddFavorite", "RemoveFavorite")
__description__ = _("Mark commonly used items and store objects for later use")
__version__ = "2009-12-30"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import typing as ty
import weakref

from kupfer import puid

# NOTE: core import
from kupfer.core import learn
from kupfer.obj import Action, Leaf, Source, SourceLeaf

if ty.TYPE_CHECKING:
    _ = str


class FavoritesSource(Source):
    """Keep a list of Leaves that the User may add and remove from"""

    instance: FavoritesSource = None  # type:ignore
    source_scan_interval: int = 3600

    def __init__(self):
        Source.__init__(self, _("Favorites"))
        ## these are default favorites for new users
        self.references: list[puid.PuID] = [
            "<kupfer.plugin.core.contents.Help>",
            "<kupfer.plugin.core.contents.Preferences>",
        ]

    def config_save(self) -> dict[str, ty.Any]:
        references = [puid.get_unique_id(F) for F in self.favorites]
        return {"favorites": references, "version": self.version}

    def config_save_name(self) -> str:
        return __name__

    def config_restore(self, state: dict[str, ty.Any]) -> None:
        self.references = state["favorites"]

    def _find_item(self, id_: puid.PuID) -> Leaf | None:
        itm = puid.resolve_unique_id(id_, excluding=self)
        if itm is None:
            return None

        assert isinstance(itm, Leaf)

        # ignore invalid objects
        if hasattr(itm, "is_valid") and not itm.is_valid():
            return None

        if puid.is_reference(id_):
            assert isinstance(id_, str)
            self.reference_table[id_] = itm
        else:
            assert isinstance(id_, puid.SerializedObject)
            self.persist_table[id_] = itm

        return itm

    # pylint: disable=attribute-defined-outside-init
    def initialize(self):
        FavoritesSource.instance = self
        self.favorites: list[Leaf] = []
        # persist_table map Serialized object to Leaves
        self.persist_table: dict[puid.SerializedObject, Leaf] = {}
        # reference table map reference-type id to leaf
        self.reference_table: weakref.WeakValueDictionary[
            str, Leaf
        ] = weakref.WeakValueDictionary()
        self.mark_for_update()

    def finalize(self) -> None:
        learn.replace_favorites(__name__)

    def _update_items(self):
        # insert items on beginning to make last added items first on list
        favorites: list[Leaf] = []
        for id_ in self.references:
            if isinstance(id_, puid.SerializedObject) and (
                leaf := self.persist_table.get(id_)
            ):
                # id_ is in persist_table so is SerializedObject
                favorites.insert(0, leaf)
                continue

            if isinstance(id_, str) and (leaf := self.reference_table.get(id_)):
                # id_ is in reference_table, so is reference, so it's str
                favorites.insert(0, leaf)
                continue

            if (itm := self._find_item(id_)) is not None:
                favorites.insert(0, itm)
            else:
                self.output_debug("MISSING:", id_)

        self.favorites = favorites

    def add(self, itm):
        if id_ := puid.get_unique_id(itm):
            # there shouldn't be possible to add twice the same leaf so
            # remove should be not needed.
            self.remove(itm)
            learn.add_favorite(__name__, itm)
            # favorites will be rebuild, so we can append
            self.favorites.append(itm)
            self.references.append(id_)
            self.mark_for_update()

    def has_item(self, itm: Leaf) -> bool:
        return itm in self.favorites

    def remove(self, itm: Leaf) -> None:
        if itm not in self.favorites:
            return

        learn.remove_favorite(__name__, itm)
        self.favorites.remove(itm)
        if id_ := puid.get_unique_id(itm):
            try:
                self.references.remove(id_)
            except KeyError:
                for key, val in self.persist_table.items():
                    if val == itm:
                        self.references.remove(key)
                        self.persist_table.pop(key)
                        break

        self.mark_for_update()

    def get_items(self):
        self._update_items()
        learn.replace_favorites(__name__, *self.favorites)

        return self.favorites

    def get_description(self):
        return _('Shelf of "Favorite" items')

    def get_icon_name(self):
        return "emblem-favorite"

    def provides(self):
        # returning nothing means it provides anything
        return ()


class AddFavorite(Action):
    # Rank down, since it applies everywhere
    rank_adjust = -15

    def __init__(self):
        Action.__init__(self, _("Add to Favorites"))

    def activate(self, leaf, iobj=None, ctx=None):
        FavoritesSource.instance.add(leaf)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return not isinstance(
            leaf, SourceLeaf
        ) and not FavoritesSource.instance.has_item(leaf)

    def get_description(self):
        return _("Add item to favorites shelf")

    def get_icon_name(self):
        return "list-add"


class RemoveFavorite(Action):
    rank_adjust = -15

    def __init__(self):
        Action.__init__(self, _("Remove from Favorites"))

    def activate(self, leaf, iobj=None, ctx=None):
        FavoritesSource.instance.remove(leaf)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return FavoritesSource.instance.has_item(leaf)

    def get_description(self):
        return _("Remove item from favorites shelf")

    def get_icon_name(self):
        return "list-remove"
