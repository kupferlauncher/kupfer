import gio
import gobject
import gtk
from hashlib import md5

from kupfer.objects import Leaf, Source, AppLeaf, Action, RunnableLeaf, SourceLeaf
from kupfer import objects, icons, utils, config
from kupfer.plugin import rhythmbox_support

__kupfer_name__ = _("Rhythmbox")
__kupfer_sources__ = ("RhythmboxSource", "RhythmboxAlbumsSource", )
__kupfer_contents__ = ("RhythmboxSource", )
__description__ = _("Rhythmbox")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

def _tostr(ustr):
	return ustr.encode("UTF-8")

def play_song(info):
	uri = _tostr(info["location"])
	utils.spawn_async(("rhythmbox-client", "--play-uri=%s" % uri))
def enqueue_songs(info, clear_queue=False):
	songs = list(info)
	if not songs:
		return
	qargv = ["rhythmbox-client"]
	if clear_queue:
		qargv.append("--clear-queue")
	for song in songs:
		uri = _tostr(song["location"])
		gfile = gio.File(uri)
		path = gfile.get_path()
		qargv.append("--enqueue")
		qargv.append(path)
	utils.spawn_async(qargv)

class PlayRhythmbox (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Play"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--play"))
	def get_description(self):
		return _("Play rhythmbox")
	def get_icon_name(self):
		return "media-playback-start"

class Next (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Next"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--next"))
	def get_description(self):
		return _("Next song in rhythmbox")
	def get_icon_name(self):
		return "media-skip-forward"

class Play (Action):
	rank_adjust = 5
	def __init__(self):
		Action.__init__(self, _("Play"))
	def activate(self, leaf):
		if isinstance(leaf, SongLeaf):
			play_song(leaf.object)
		if isinstance(leaf, AlbumLeaf):
			songs = list(leaf.object)
			if not songs:
				return
			# play first, enqueue others
			play_song(songs[0])
			enqueue_songs(songs[1:], clear_queue=True)

	def get_icon_name(self):
		return "media-playback-start"

class Enqueue (Action):
	def __init__(self):
		Action.__init__(self, _("Enqueue"))
	def activate(self, leaf):
		if isinstance(leaf, SongLeaf):
			enqueue_songs((leaf.object, ))
		if isinstance(leaf, AlbumLeaf):
			songs = list(leaf.object)
			if not songs:
				return
			enqueue_songs(songs)

	def get_description(self):
		return _("Put song in the queue")
	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "media-playback-start")
	def get_icon_name(self):
		return "media-playback-start"

class SongLeaf (Leaf):
	def __init__(self, name, artist, info):
		Leaf.__init__(self, info, name)
		self.artist = artist
	def get_actions(self):
		yield Play()
		yield Enqueue()
	def get_description(self):
		# TRANS: Song description
		return _("%s by %s") % (unicode(self), self.artist)
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
	def get_actions(self):
		yield Play()
		yield Enqueue()
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		return AlbumSource(unicode(self), self.object)
	def get_description(self):
		artist = None
		for song in self.object:
			if not artist:
				artist = song["artist"]
			elif artist != song["artist"]:
				# TRANS: Multiple artist description "Artist1 et. al. "
				artist = _("%s et. al.") % artist
				break
		# TRANS: Album description
		return _("%s by %s") % (unicode(self), artist)
	def get_thumbnail(self, width, height):
		if not hasattr(self, "cover_file"):
			ltitle = unicode(self).lower()
			# ignore the track artist -- use the space fallback
			# hash of ' ' as fallback
			hspace = "7215ee9c7d9dc229d2921a40e899ec5f"
			htitle = md5(_tostr(ltitle)).hexdigest()
			hartist = hspace
			cache_name = "album-%s-%s.jpeg" % (hartist, htitle)
			cache_file = config.get_cache_file(("media-art", cache_name))
			self.cover_file = cache_file
		if self.cover_file:
			try:
				return gtk.gdk.pixbuf_new_from_file_at_size(self.cover_file,
						width, height)
			except gobject.GError:
				pass
		return None

	def get_icon_name(self):
		return "media-optical"

class RhythmboxAlbumsSource (Source):
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

	def get_gicon(self):
		return icons.ComposedIcon("rhythmbox", "media-optical")
	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield AlbumLeaf

class RhythmboxSource (Source):
	def __init__(self):
		Source.__init__(self, _("Rhythmbox"))
	def is_dynamic(self):
		return True
	def get_items(self):
		yield PlayRhythmbox()
		yield Next()
		yield SourceLeaf(RhythmboxAlbumsSource())

	def get_description(self):
		return _("Rhythmbox action and its library")
	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield RunnableLeaf
		yield SourceLeaf
	def get_leaf_repr(self):
		try:
			app = objects.AppLeaf(item_id="rhythmbox.desktop")
		except objects.InvalidDataError:
			app = None
		return app
	@classmethod
	def decorates_type(cls):
		return AppLeaf
	@classmethod
	def decorate_item(cls, leaf):
		if leaf.get_id() == "rhythmbox.desktop":
			return cls()
