__kupfer_name__ = _("Audacious")
__kupfer_sources__ = ("AudaciousSource", )
__kupfer_actions__ = (
		"Rescan",
	)
__description__ = _("Control Audacious playback and playlist")
__version__ = "2009-12-15"
__author__ = "Horia V. Corcalciuc <h.v.corcalciuc@gmail.com>"

import subprocess

from kupfer.objects import Leaf, Source, Action
from kupfer.objects import AppLeaf, RunnableLeaf, SourceLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import objects, icons, utils
from kupfer import plugin_support
from kupfer import kupferstring

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key": "playlist_toplevel",
		"label": _("Include songs in top level"),
		"type": bool,
		"value": True,
	},
)

AUDTOOL = "audtool2"
AUDACIOUS = "audacious2"

def enqueue_song(info):
	utils.spawn_async((AUDTOOL, "playqueue-add", "%d" % info))

def dequeue_song(info):
	utils.spawn_async((AUDTOOL, "playqueue-remove", "%d" % info))

def play_song(info):
	utils.spawn_async((AUDTOOL, "playlist-jump", "%d" % info))
	utils.spawn_async((AUDTOOL, "playback-play"))

def get_playlist_songs():
	"""Yield tuples of (position, name) for playlist songs"""
	toolProc = subprocess.Popen([AUDTOOL, "playlist-display"],
			stdout=subprocess.PIPE)
	stdout, stderr = toolProc.communicate()
	for line in stdout.splitlines():
		if not line.count('|') >= 2:
			continue
		position, rest = line.split('|', 1)
		songname, rest = rest.rsplit('|', 1)
		pos = int(position.strip())
		nam = kupferstring.fromlocale(songname.strip())
		yield (pos, nam)

def clear_queue():
	utils.spawn_async((AUDTOOL, "playqueue-clear"))

class Enqueue (Action):
	def __init__(self):
		Action.__init__(self, _("Enqueue"))
	def activate(self, leaf):
		enqueue_song(leaf.object)
	def get_description(self):
		return _("Add track to the Audacious play queue")
	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "media-playback-start")
	def get_icon_name(self):
		return "media-playback-start"

class Dequeue (Action):
	def __init__(self):
		Action.__init__(self, _("Dequeue"))
	def activate(self, leaf):
		dequeue_song(leaf.object)
	def get_description(self):
		return _("Remove track from the Audacious play queue")
	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "media-playback-stop")
	def get_icon_name(self):
		return "media-playback-stop"

class JumpToSong(Action):
	def __init__(self):
		Action.__init__(self, _("Play"))
	def activate(self, leaf):
		play_song(leaf.object)
	def get_description(self):
		return _("Jump to track in Audacious")
	def get_icon_name(self):
		return "media-playback-start"

class Rescan (Action):
	"""A source action: Rescan a source!

	A simplified version of the original core Rescan action
	"""
	rank_adjust = -5
	def __init__(self):
		Action.__init__(self, _("Rescan"))

	def activate(self, leaf):
		if not leaf.has_content():
			raise objects.InvalidLeafError("Must have content")
		source = leaf.content_source()
		source.get_leaves(force_update=True)

	def get_description(self):
		return _("Force reindex of this source")
	def get_icon_name(self):
		return "gtk-refresh"
	def item_types(self):
		yield AppLeaf
	def valid_for_item(self, item):
		return item.get_id() == AUDACIOUS

class Play (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Play"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playback-play"))
	def get_description(self):
		return _("Resume playback in Audacious")
	def get_icon_name(self):
		return "media-playback-start"

class Pause (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Pause"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playback-pause"))
	def get_description(self):
		return _("Pause playback in Audacious")
	def get_icon_name(self):
		return "media-playback-pause"

class Next (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Next"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playlist-advance"))
	def get_description(self):
		return _("Jump to next track in Audacious")
	def get_icon_name(self):
		return "media-skip-forward"

class Previous (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Previous"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playlist-reverse"))
	def get_description(self):
		return _("Jump to previous track in Audacious")
	def get_icon_name(self):
		return "media-skip-backward"

class ClearQueue (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Clear Queue"))
	def run(self):
		clear_queue()
	def get_description(self):
		return _("Clear the Audacious play queue")
	def get_icon_name(self):
		return "edit-clear"
		
class Shuffle (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Shuffle"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playlist-shuffle-toggle"))
	def get_description(self):
		return _("Toggle shuffle in Audacious")
	def get_icon_name(self):
		return "media-playlist-shuffle"

class Repeat (RunnableLeaf):
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Repeat"))
	def run(self):
		utils.spawn_async((AUDTOOL, "playlist-repeat-toggle"))
	def get_description(self):
		return _("Toggle repeat in Audacious")
	def get_icon_name(self):
		return "media-playlist-repeat"

class SongLeaf (Leaf):
	"""The SongLeaf's represented object is the Playlist index"""
	def get_actions(self):
		yield JumpToSong()
		yield Enqueue()
		yield Dequeue()
	def get_icon_name(self):
		return "audio-x-generic"

class AudaciousSongsSource (Source):
	def __init__(self, library):
		Source.__init__(self, _("Playlist"))
		self.library = library
	def get_items(self):
		for song in self.library:
			yield SongLeaf(*song)
	def get_gicon(self):
		return icons.ComposedIcon(AUDACIOUS, "audio-x-generic",
			emblem_is_fallback=True)
	def provides(self):
		yield SongLeaf

class AudaciousSource (AppLeafContentMixin, Source):
	appleaf_content_id = AUDACIOUS
	def __init__(self):
		Source.__init__(self, _("Audacious"))
	def get_items(self):
		yield Play()
		yield Pause()
		yield Next()
		yield Previous() 
		yield ClearQueue()
		# Commented as these seem to have no effect
		#yield Shuffle()
		#yield Repeat()
		songs = list(get_playlist_songs())
		songs_source = AudaciousSongsSource(songs)
		yield SourceLeaf(songs_source)
		if __kupfer_settings__["playlist_toplevel"]:
			for leaf in songs_source.get_leaves():
				yield leaf
	def get_description(self):
		return __description__
	def get_icon_name(self):
		return AUDACIOUS
	def provides(self):
		yield RunnableLeaf
