__kupfer_name__ = _("Audacious")
__kupfer_sources__ = ("AudaciousSource", )
__description__ = _("Control Audacious playback and playlist")
__version__ = "2017.2"
__author__ = "Horia V. Corcalciuc <h.v.corcalciuc@gmail.com>, US"

import subprocess

from kupfer.objects import Leaf, Source, Action
from kupfer.objects import RunnableLeaf, SourceLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import icons, utils, uiutils
from kupfer import plugin_support
from kupfer import kupferstring
from kupfer.weaklib import dbus_signal_connect_weakly

plugin_support.check_dbus_connection()

import dbus

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "playlist_toplevel",
        "label": _("Include songs in top level"),
        "type": bool,
        "value": True,
    },
)

AUDTOOL = "audtool"
AUDACIOUS = "audacious"
_BUS_NAME = "org.atheme.audacious"

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
        if not line.count(b'|') >= 2:
            continue
        position, rest = line.split(b'|', 1)
        songname, rest = rest.rsplit(b'|', 1)
        pos = int(position.strip())
        nam = kupferstring.fromlocale(songname.strip())
        yield (pos, nam)

def get_current_song():
    toolProc = subprocess.Popen([AUDTOOL, "current-song"],
            stdout=subprocess.PIPE)
    stdout, stderr = toolProc.communicate()
    for line in stdout.splitlines():
        return kupferstring.fromlocale(line)
    return None

def clear_queue():
    utils.spawn_async((AUDTOOL, "playqueue-clear"))

class Enqueue (Action):
    action_accelerator = "e"
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
    action_accelerator = "o"
    def __init__(self):
        Action.__init__(self, _("Play"))
    def activate(self, leaf):
        play_song(leaf.object)
    def get_description(self):
        return _("Jump to track in Audacious")
    def get_icon_name(self):
        return "media-playback-start"

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

class ShowPlaying (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Show Playing"))
    def run(self):
        song = get_current_song()
        if song is not None:
            uiutils.show_notification(song, icon_name="audio-x-generic")
    def get_description(self):
        return _("Tell which song is currently playing")
    def get_gicon(self):
        return icons.ComposedIcon("dialog-information", "audio-x-generic")
    def get_icon_name(self):
        return "dialog-information"

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
    source_user_reloadable = True

    def __init__(self):
        Source.__init__(self, _("Audacious"))

    def initialize(self):
        bus = dbus.SessionBus()
        dbus_signal_connect_weakly(bus, "NameOwnerChanged", self._name_owner_changed,
                                   dbus_interface="org.freedesktop.DBus",
                                   arg0=_BUS_NAME)

    def _name_owner_changed(self, name, old, new):
        if new:
            self.mark_for_update()

    def get_items(self):
        yield Play()
        yield Pause()
        yield Next()
        yield Previous() 
        yield ClearQueue()
        yield ShowPlaying()
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
