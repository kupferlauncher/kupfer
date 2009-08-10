from kupfer.objects import Leaf, Source, AppLeaf, Action, FileLeaf
from kupfer import objects
from kupfer.plugin import rhythmbox_support

__kupfer_name__ = _("Rhythmbox")
__kupfer_sources__ = ("RhythmboxAlbumsSource", )
__description__ = _("Rhythmbox")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


class AlbumLeaf (Leaf):
	def __init__(self, name, artist, info):
		Leaf.__init__(self, info, name)
		self.artist = artist
	def get_icon_name(self):
		return "media-optical"

class RhythmboxAlbumsSource (Source):
	"""
	"""
	def __init__(self):
		Source.__init__(self, _("Rhythmbox Albums"))
	
	def get_items(self):
		library = rhythmbox_support.get_rhythmbox_artist_albums()
		for artist in library:
			for album in library[artist]:
				yield AlbumLeaf(album, artist, library[artist][album])
	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("Albums")

	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield AlbumLeaf

