__kupfer_name__ = _("Favorites")
__kupfer_sources__ = ("FavoritesSource", )
__kupfer_actions__ = ("AddFavorite", "RemoveFavorite", )
__description__ = _("Mark commonly used items and store objects for later use")
__version__ = "2009-12-30"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import weakref

from kupfer.objects import Leaf, Source, Action
from kupfer import puid

# NOTE: core import
from kupfer.core import learn


class FavoritesSource (Source):
    """Keep a list of Leaves that the User may add and remove from"""
    instance = None
    def __init__(self):
        Source.__init__(self, _("Favorites"))
        ## these are default favorites for new users
        self.references = [
                '<kupfer.plugin.core.contents.Help>',
                '<kupfer.plugin.core.contents.Preferences>',
            ]

    def config_save(self):
        references = [puid.get_unique_id(F) for F in self.favorites]
        return {"favorites": references, "version": self.version}

    def config_save_name(self):
        return __name__

    def config_restore(self, state):
        self.references = state["favorites"]

    def _lookup_item(self, id_):
        itm = puid.resolve_unique_id(id_, excluding=self)
        if itm is None:
            return None
        return itm

    def _valid_item(self,  itm):
        if hasattr(itm, "is_valid") and not itm.is_valid():
            return False
        return True

    def _find_item(self, id_):
        itm = self._lookup_item(id_)
        if itm is None or not self._valid_item(itm):
            return None
        if puid.is_reference(id_):
            self.reference_table[id_] = itm
        else:
            self.persist_table[id_] = itm
        return itm

    def initialize(self):
        FavoritesSource.instance = self
        self.favorites = []
        self.persist_table = {}
        self.reference_table = weakref.WeakValueDictionary()
        self.mark_for_update()

    def _update_items(self):
        self.favorites = []
        self.mark_for_update()
        for id_ in self.references:
            if id_ in self.persist_table:
                self.favorites.append(self.persist_table[id_])
                continue
            if id_ in self.reference_table:
                self.favorites.append(self.reference_table[id_])
                continue
            itm = self._find_item(id_)
            if itm is None:
                self.output_debug("MISSING:", id_)
            else:
                self.favorites.append(itm)

    @classmethod
    def add(cls, itm):
        cls.instance._add(itm)

    def _add(self, itm):
        if self._has_item(itm):
            self._remove(itm)
        learn.add_favorite(itm)
        self.favorites.append(itm)
        self.references.append(puid.get_unique_id(itm))
        self.mark_for_update()

    @classmethod
    def has_item(cls, itm):
        return cls.instance._has_item(itm)

    def _has_item(self, itm):
        return itm in set(self.favorites)

    @classmethod
    def remove(cls, itm):
        if cls.has_item(itm):
            cls.instance._remove(itm)

    def _remove(self, itm):
        learn.remove_favorite(itm)
        self.favorites.remove(itm)
        id_ = puid.get_unique_id(itm)
        if id_ in self.references:
            self.references.remove(id_)
        else:
            for key, val in self.persist_table.items():
                if val == itm:
                    self.references.remove(key)
                    self.persist_table.pop(key)
                    break
        self.mark_for_update()

    def get_items(self):
        self._update_items()
        for fav in self.favorites:
            learn.add_favorite(fav)
        return reversed(self.favorites)

    def get_description(self):
        return _('Shelf of "Favorite" items')

    def get_icon_name(self):
        return "emblem-favorite"

    def provides(self):
        # returning nothing means it provides anything
        return ()

class AddFavorite (Action):
    # Rank down, since it applies everywhere
    rank_adjust = -15
    def __init__(self):
        Action.__init__(self, _("Add to Favorites"))
    def activate(self, leaf):
        FavoritesSource.add(leaf)
    def item_types(self):
        return (Leaf, )
    def valid_for_item(self, item):
        return not FavoritesSource.has_item(item)
    def get_description(self):
        return _("Add item to favorites shelf")
    def get_icon_name(self):
        return "list-add"

class RemoveFavorite (Action):
    rank_adjust = -15
    def __init__(self):
        Action.__init__(self, _("Remove from Favorites"))
    def activate(self, leaf):
        FavoritesSource.remove(leaf)
    def item_types(self):
        return (Leaf, )
    def valid_for_item(self, item):
        return FavoritesSource.has_item(item)
    def get_description(self):
        return _("Remove item from favorites shelf")
    def get_icon_name(self):
        return "list-remove"
