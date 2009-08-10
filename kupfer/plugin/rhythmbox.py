from kupfer.objects import Leaf, Source, AppLeaf, Action, FileLeaf
from kupfer import objects
from kupfer.plugin import rhythmbox_support

__kupfer_name__ = _("Rhythmbox")
__kupfer_sources__ = ("RhythmboxAlbumsSource", )
__description__ = _("Rhythmbox")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class SongLeaf (Leaf):
	def __init__(self, name, artist, info):
		Leaf.__init__(self, info, name)
		self.artist = artist
	def get_icon_name(self):
		return "audio-x-generic"

class AlbumSource (Source):
	def __init__(self, name, info):
		Source.__init__(self, name)
		self.info = info
	def get_items(self):
		for song in self.info:
			yield SongLeaf(song["title"], song["artist"], song)
	def get_icon_name(self):
		return "media-optical"

class AlbumLeaf (Leaf):
	def __init__(self, name, info):
		Leaf.__init__(self, info, name)
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		return AlbumSource(unicode(self), self.object)
	def get_icon_name(self):
		return "media-optical"

class RhythmboxAlbumsSource (Source):
	"""
	"""
	def __init__(self):
		Source.__init__(self, _("Rhythmbox Albums"))
	
	def get_items(self):
		library = rhythmbox_support.get_rhythmbox_albums()
		for album in library:
			yield AlbumLeaf(album, library[album])
	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("Albums")

	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield AlbumLeaf

