from collections import deque
import weakref

import gtk

from kupfer.objects import Source, Action, PicklingHelperMixin
from kupfer import utils, objects, pretty

__kupfer_name__ = _("Favorites")
__kupfer_sources__ = ("FavoritesSource", )
__kupfer_actions__ = ("AddFavorite", "RemoveFavorite", )
__description__ = _("(Simple) favorites plugin")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

def _FavoritesLeafTypes():
	"""reasonable pickleable types"""
	yield objects.FileLeaf
	yield objects.AppLeaf
	yield objects.UrlLeaf

class FavoritesSource (Source, PicklingHelperMixin):
	"""Keep a list of Leaves that the User may add and remove from"""
	def __init__(self):
		Source.__init__(self, _("Favorites"))
		self.favorites = deque()
		self.unpickle_finish()

	def unpickle_finish(self):
		RegisterFavoritesSource(self)
		# check items for validity
		for itm in list(self.favorites):
			if hasattr(itm, "is_valid") and not itm.is_valid():
				self.output_debug("Removing invalid leaf", itm)
				self.favorites.remove(itm)

	def add(self, itm):
		self.favorites.append(itm)
		self.mark_for_update()

	def has_item(self, itm):
		return itm in set(self.favorites)

	def remove(self, itm):
		self.favorites.remove(itm)
		self.mark_for_update()

	def get_items(self):
		for t in reversed(self.favorites):
			yield t

	def get_description(self):
		return _('Shelf of "Favorite" items')

	def get_icon_name(self):
		return "emblem-favorite"

	def provides(self):
		return list(_FavoritesLeafTypes())

_favorites_source = []

def RegisterFavoritesSource(fav):
	_favorites_source.append(weakref.ref(fav))

def GetFavoritesSource():
	for favref in list(_favorites_source):
		if favref() is None:
			_favorites_source.remove(favref)
	if len(_favorites_source) > 1:
		pretty.print_error("have > 1 favorites source")

	try:
		return _favorites_source[0]()
	except IndexError:
		raise LookupError("Favorites Source not found")

class AddFavorite (Action):
	def __init__(self):
		Action.__init__(self, _("Add to Favorites"))
	def activate(self, leaf):
		GetFavoritesSource().add(leaf)
	def item_types(self):
		return list(_FavoritesLeafTypes())
	def valid_for_item(self, item):
		return not GetFavoritesSource().has_item(item)
	def get_description(self):
		return _("Add item to favorites shelf")
	def get_icon_name(self):
		return "gtk-add"

class RemoveFavorite (Action):
	def __init__(self):
		Action.__init__(self, _("Remove from Favorites"))
	def activate(self, leaf):
		GetFavoritesSource().remove(leaf)
	def item_types(self):
		return list(_FavoritesLeafTypes())
	def valid_for_item(self, item):
		return GetFavoritesSource().has_item(item)
	def get_description(self):
		return _("Remove item from favorites shelf")
	def get_icon_name(self):
		return "gtk-remove"
