__kupfer_name__ = _("Audacious")
__kupfer_sources__ = ("AudaciousSource",)
__description__ = _("Control Audacious playback and playlist")
__version__ = "2017.2"
__author__ = "Horia V. Corcalciuc <h.v.corcalciuc@gmail.com>, US"

import subprocess
import typing as ty

import dbus

from kupfer import icons, plugin_support, utils
from kupfer.obj import Action, Leaf, RunnableLeaf, Source, SourceLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.support import kupferstring, weaklib
from kupfer.ui import uiutils

plugin_support.check_dbus_connection()

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "playlist_toplevel",
        "label": _("Include songs in top level"),
        "type": bool,
        "value": True,
    },
)

if ty.TYPE_CHECKING:
    _ = str

_AUDTOOL = "audtool"
_AUDACIOUS = "audacious"
_BUS_NAME = "org.atheme.audacious"


def enqueue_song(info):
    utils.spawn_async((_AUDTOOL, "playqueue-add", str(info)))


def dequeue_song(info):
    utils.spawn_async((_AUDTOOL, "playqueue-remove", str(info)))


def play_song(info):
    utils.spawn_async((_AUDTOOL, "playlist-jump", str(info)))
    utils.spawn_async((_AUDTOOL, "playback-play"))


def get_playlist_songs():
    """Yield tuples of (position, name) for playlist songs"""
    with subprocess.Popen(
        [_AUDTOOL, "playlist-display"], stdout=subprocess.PIPE
    ) as proc:
        stdout, _stderr = proc.communicate()
        for line in stdout.splitlines():
            if not line.count(b"|") >= 2:
                continue

            position, rest = line.split(b"|", 1)
            songname, rest = rest.rsplit(b"|", 1)
            pos = int(position.strip())
            nam = kupferstring.fromlocale(songname.strip())
            yield (pos, nam)


def get_current_song():
    with subprocess.Popen(
        [_AUDTOOL, "current-song"], stdout=subprocess.PIPE
    ) as proc:
        stdout, _stderr = proc.communicate()
        for line in stdout.splitlines():
            return kupferstring.fromlocale(line)

        return None


def clear_queue():
    utils.spawn_async((_AUDTOOL, "playqueue-clear"))


class Enqueue(Action):
    action_accelerator = "e"

    def __init__(self):
        Action.__init__(self, _("Enqueue"))

    def activate(self, leaf, iobj=None, ctx=None):
        enqueue_song(leaf.object)

    def get_description(self):
        return _("Add track to the Audacious play queue")

    def get_gicon(self):
        return icons.ComposedIcon("gtk-execute", "media-playback-start")

    def get_icon_name(self):
        return "media-playback-start"


class Dequeue(Action):
    def __init__(self):
        Action.__init__(self, _("Dequeue"))

    def activate(self, leaf, iobj=None, ctx=None):
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

    def activate(self, leaf, iobj=None, ctx=None):
        play_song(leaf.object)

    def get_description(self):
        return _("Jump to track in Audacious")

    def get_icon_name(self):
        return "media-playback-start"


class Play(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Play"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playback-play"))

    def get_description(self):
        return _("Resume playback in Audacious")

    def get_icon_name(self):
        return "media-playback-start"


class Pause(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Pause"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playback-pause"))

    def get_description(self):
        return _("Pause playback in Audacious")

    def get_icon_name(self):
        return "media-playback-pause"


class Next(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Next"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playlist-advance"))

    def get_description(self):
        return _("Jump to next track in Audacious")

    def get_icon_name(self):
        return "media-skip-forward"


class Previous(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Previous"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playlist-reverse"))

    def get_description(self):
        return _("Jump to previous track in Audacious")

    def get_icon_name(self):
        return "media-skip-backward"


class ClearQueue(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Clear Queue"))

    def run(self, ctx=None):
        clear_queue()

    def get_description(self):
        return _("Clear the Audacious play queue")

    def get_icon_name(self):
        return "edit-clear"


class Shuffle(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Shuffle"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playlist-shuffle-toggle"))

    def get_description(self):
        return _("Toggle shuffle in Audacious")

    def get_icon_name(self):
        return "media-playlist-shuffle"


class Repeat(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Repeat"))

    def run(self, ctx=None):
        utils.spawn_async((_AUDTOOL, "playlist-repeat-toggle"))

    def get_description(self):
        return _("Toggle repeat in Audacious")

    def get_icon_name(self):
        return "media-playlist-repeat"


class ShowPlaying(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Show Playing"))

    def run(self, ctx=None):
        song = get_current_song()
        if song is not None:
            uiutils.show_notification(song, icon_name="audio-x-generic")

    def get_description(self):
        return _("Tell which song is currently playing")

    def get_gicon(self):
        return icons.ComposedIcon("dialog-information", "audio-x-generic")

    def get_icon_name(self):
        return "dialog-information"


class SongLeaf(Leaf):
    """The SongLeaf's represented object is the Playlist index"""

    def get_actions(self):
        yield JumpToSong()
        yield Enqueue()
        yield Dequeue()

    def get_icon_name(self):
        return "audio-x-generic"


class AudaciousSongsSource(Source):
    def __init__(self, library):
        Source.__init__(self, _("Playlist"))
        self.library = library

    def get_items(self):
        for song in self.library:
            yield SongLeaf(*song)

    def get_gicon(self):
        return icons.ComposedIcon(
            _AUDACIOUS, "audio-x-generic", emblem_is_fallback=True
        )

    def provides(self):
        yield SongLeaf


class AudaciousSource(AppLeafContentMixin, Source):
    appleaf_content_id = _AUDACIOUS
    source_user_reloadable = True

    def __init__(self):
        Source.__init__(self, _("Audacious"))

    def initialize(self):
        bus = dbus.SessionBus()
        weaklib.dbus_signal_connect_weakly(
            bus,
            "NameOwnerChanged",
            self._name_owner_changed,
            dbus_interface="org.freedesktop.DBus",
            arg0=_BUS_NAME,
        )

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
        # yield Shuffle()
        # yield Repeat()
        songs = list(get_playlist_songs())
        songs_source = AudaciousSongsSource(songs)
        yield SourceLeaf(songs_source)
        if __kupfer_settings__["playlist_toplevel"]:
            yield from songs_source.get_leaves()

    def get_description(self):
        return __description__

    def get_icon_name(self):
        return _AUDACIOUS

    def provides(self):
        yield RunnableLeaf
