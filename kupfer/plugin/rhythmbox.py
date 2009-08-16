import gio
from hashlib import md5

from kupfer.objects import (Leaf, Source, AppLeaf, Action, RunnableLeaf,
		SourceLeaf, AppLeafContentMixin)
from kupfer import objects, icons, utils, config
from kupfer import plugin_support
from kupfer.plugin import rhythmbox_support

__kupfer_name__ = _("Rhythmbox")
__kupfer_sources__ = (
		"RhythmboxSource",
	)
__kupfer_contents__ = ("RhythmboxSource", )
__description__ = _("Play and enqueue tracks and browse the music library")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "toplevel_artists",
		"label": _("Include artists in top level"),
		"type": bool,
		"value": True,
	},
	{
		"key" : "toplevel_albums",
		"label": _("Include albums in top level"),
		"type": bool,
		"value": False,
	},
	{
		"key" : "toplevel_songs",
		"label": _("Include songs in top level"),
		"type": bool,
		"value": False,
	},
)

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

class Play (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Play"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--play"))
	def get_description(self):
		return _("Resume playback in Rhythmbox")
	def get_icon_name(self):
		return "media-playback-start"

class Pause (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Pause"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--no-start", "--pause"))
	def get_description(self):
		return _("Pause playback in Rhythmbox")
	def get_icon_name(self):
		return "media-playback-pause"

class Next (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Next"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--no-start", "--next"))
	def get_description(self):
		return _("Jump to next track in Rhythmbox")
	def get_icon_name(self):
		return "media-skip-forward"

class Previous (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Previous"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--no-start", "--previous"))
	def get_description(self):
		return _("Jump to previous track in Rhythmbox")
	def get_icon_name(self):
		return "media-skip-backward"

class ShowPlaying (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Show Playing"))
	def run(self):
		utils.spawn_async(("rhythmbox-client", "--no-start", "--notify"))
	def get_description(self):
		return _("Tell which song is currently playing")
	def get_gicon(self):
		return icons.ComposedIcon("dialog-information", "audio-x-generic")
	def get_icon_name(self):
		return "dialog-information"

class PlayTracks (Action):
	rank_adjust = 5
	def __init__(self):
		Action.__init__(self, _("Play"))
	def activate(self, leaf):
		if isinstance(leaf, SongLeaf):
			play_song(leaf.object)
		if isinstance(leaf, TrackCollection):
			songs = list(leaf.object)
			if not songs:
				return
			# play first, enqueue others
			play_song(songs[0])
			enqueue_songs(songs[1:], clear_queue=True)

	def get_description(self):
		return _("Play tracks in Rhythmbox")
	def get_icon_name(self):
		return "media-playback-start"

class Enqueue (Action):
	def __init__(self):
		Action.__init__(self, _("Enqueue"))
	def activate(self, leaf):
		if isinstance(leaf, SongLeaf):
			enqueue_songs((leaf.object, ))
		if isinstance(leaf, TrackCollection):
			songs = list(leaf.object)
			if not songs:
				return
			enqueue_songs(songs)

	def get_description(self):
		return _("Add tracks to the play queue")
	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "media-playback-start")
	def get_icon_name(self):
		return "media-playback-start"

class SongLeaf (Leaf):
	def __init__(self, info, name=None):
		"""Init with song info
		@info: Song information dictionary
		"""
		if not name: name = info["title"]
		Leaf.__init__(self, info, name)
	def repr_key(self):
		"""To distinguish songs by the same name"""
		return (self.object["title"], self.object["artist"],
				self.object["album"])
	def get_actions(self):
		yield PlayTracks()
		yield Enqueue()
	def get_description(self):
		# TRANS: Song description
		return _("by %(artist)s from %(album)s") % {
				"artist": self.object["artist"],
				"album": self.object["album"],
				}
	def get_icon_name(self):
		return "audio-x-generic"

class CollectionSource (Source):
	def __init__(self, leaf):
		Source.__init__(self, unicode(leaf))
		self.leaf = leaf
	def get_items(self):
		for song in self.leaf.object:
			yield SongLeaf(song)
	def get_description(self):
		return self.leaf.get_description()
	def get_thumbnail(self, w, h):
		return self.leaf.get_thumbnail(w, h)
	def get_gicon(self):
		return self.leaf.get_gicon()
	def get_icon_name(self):
		return self.leaf.get_icon_name()

class TrackCollection (Leaf):
	"""A generic track collection leaf, such as one for
	an Album or an Artist
	"""
	def __init__(self, info, name):
		"""Init with track collection
		@info: Should be a sequence of song information dictionaries
		"""
		Leaf.__init__(self, info, name)
	def get_actions(self):
		yield PlayTracks()
		yield Enqueue()
	def has_content(self):
		return True
	def content_source(self, alternate=False):
		return CollectionSource(self)
	def get_icon_name(self):
		return "media-optical"

class AlbumLeaf (TrackCollection):
	def get_description(self):
		artist = None
		for song in self.object:
			if not artist:
				artist = song["artist"]
			elif artist != song["artist"]:
				# TRANS: Multiple artist description "Artist1 et. al. "
				artist = _("%s et. al.") % artist
				break
		# TRANS: Album description "by Artist"
		return _("by %s") % (artist, )
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
			# now try filesystem
			if not cache_file:
				uri = self.object[0]["location"]
				gfile = gio.File(uri)
				for cover_name in ("album.jpg", "cover.jpg"):
					cfile = gfile.resolve_relative_path("../" + cover_name)
					if cfile.query_exists():
						cache_file = cfile.get_path()
						break
			self.cover_file = cache_file
		return icons.get_pixbuf_from_file(self.cover_file, width, height)

class ArtistAlbumsSource (CollectionSource):
	def get_items(self):
		albums = {}
		for song in self.leaf.object:
			album = song["album"]
			album_list = albums.get(album, [])
			album_list.append(song)
			albums[album] = album_list
		for album in albums:
			yield AlbumLeaf(albums[album], album)
	def should_sort_lexically(self):
		return True

class ArtistLeaf (TrackCollection):
	def get_description(self):
		# TRANS: Artist songs collection description
		return _("Tracks by %s") % (unicode(self), )
	def get_gicon(self):
		return icons.ComposedIcon("media-optical", "system-users")
	def content_source(self, alternate=False):
		if alternate:
			return CollectionSource(self)
		return ArtistAlbumsSource(self)

class RhythmboxAlbumsSource (Source):
	def __init__(self, library):
		Source.__init__(self, _("Albums"))
		self.library = library
	
	def get_items(self):
		for album in self.library:
			yield AlbumLeaf(self.library[album], album)
	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("Music albums in Rhythmbox Library")
	def get_gicon(self):
		return icons.ComposedIcon("rhythmbox", "media-optical",
				emblem_is_fallback=True)
	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield AlbumLeaf

class RhythmboxArtistsSource (Source):
	def __init__(self, library):
		Source.__init__(self, _("Artists"))
		self.library = library

	def get_items(self):
		for artist in self.library:
			yield ArtistLeaf(self.library[artist], artist)
	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("Music artists in Rhythmbox Library")
	def get_gicon(self):
		return icons.ComposedIcon("rhythmbox", "system-users",
				emblem_is_fallback=True)
	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield ArtistLeaf

def _locale_sort_artist_album_songs(artists):
	"""Sort by Artist, then Album, then Track"""
	for artist in utils.locale_sort(artists):
		artist_songs = artists[artist]
		albums = set(s["album"] for s in artist_songs)
		for album in utils.locale_sort(albums):
			album_songs = []
			for song in artist_songs:
				if song["album"] == album:
					album_songs.append(song)
			album_songs.sort(key=lambda s: s.get("track-number", u""))
			for song in album_songs:
				yield song

class RhythmboxSongsSource (Source):
	"""The whole song library in Leaf representation"""
	def __init__(self, library):
		Source.__init__(self, _("Songs"))
		self.library = library

	def get_items(self):
		for song in _locale_sort_artist_album_songs(self.library):
			yield SongLeaf(song)

	def get_actions(self):
		return ()
	def get_description(self):
		return _("Songs in Rhythmbox library")
	def get_gicon(self):
		return icons.ComposedIcon("rhythmbox", "audio-x-generic",
				emblem_is_fallback=True)
	def provides(self):
		yield SongLeaf

class RhythmboxSource (AppLeafContentMixin, Source):
	appleaf_content_id = "rhythmbox.desktop"
	def __init__(self):
		Source.__init__(self, _("Rhythmbox"))
	def get_items(self):
		try:
			songs = rhythmbox_support.get_rhythmbox_songs()
		except StandardError, e:
			self.output_error(e)
			songs = []
		albums = rhythmbox_support.parse_rhythmbox_albums(songs)
		artists = rhythmbox_support.parse_rhythmbox_artists(songs)
		yield Play()
		yield Pause()
		yield Next()
		yield Previous()
		yield ShowPlaying()
		artist_source = RhythmboxArtistsSource(artists)
		album_source = RhythmboxAlbumsSource(albums)
		songs_source = RhythmboxSongsSource(artists)
		yield SourceLeaf(artist_source)
		yield SourceLeaf(album_source)
		yield SourceLeaf(songs_source)
		# cache the subsources
		for src in (artist_source, album_source, songs_source):
			src.get_leaves()
		# we use get_leaves here to get sorting etc right
		if __kupfer_settings__["toplevel_artists"]:
			for leaf in artist_source.get_leaves():
				yield leaf
		if __kupfer_settings__["toplevel_albums"]:
			for leaf in album_source.get_leaves():
				yield leaf
		if __kupfer_settings__["toplevel_songs"]:
			for leaf in songs_source.get_leaves():
				yield leaf

	def get_description(self):
		return _("Play and enqueue tracks and browse the music library")
	def get_icon_name(self):
		return "rhythmbox"
	def provides(self):
		yield RunnableLeaf
		yield SourceLeaf
		yield SongLeaf
