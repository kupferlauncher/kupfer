from __future__ import annotations

__kupfer_name__ = _("Audacious")
__kupfer_sources__ = ("AudaciousSource",)
__description__ = _("Control Audacious playback and playlist")
__version__ = "2023.1"
__author__ = "Horia V. Corcalciuc <h.v.corcalciuc@gmail.com>, US, KB"

# TODO: support many playlists (?); for now we load only active playlist

import subprocess
import typing as ty

import dbus

from kupfer import icons, launch, plugin_support
from kupfer.obj import (
    Action,
    Leaf,
    NotAvailableError,
    RunnableLeaf,
    Source,
    SourceLeaf,
)
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.support import kupferstring, pretty, weaklib
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
_OBJ_NAME = "/org/atheme/audacious"
_IFACE_NAME = "org.atheme.audacious"


def _create_dbus_connection(
    iface: str, obj: str, service: str
) -> dbus.Interface:
    """Create dbus connection to NetworkManager"""
    try:
        sbus = dbus.SessionBus()
        if dobj := sbus.get_object(service, obj):
            return dbus.Interface(dobj, iface)

    except dbus.exceptions.DBusException as err:
        pretty.print_debug(__name__, err)
        raise NotAvailableError(service) from err

    raise NotAvailableError(service)


def get_playlist_songs_dbus() -> ty.Iterator[SongLeaf]:
    conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
    total = conn.Length()
    for pos in range(1, total + 1):
        title = " ".join(
            (conn.SongTuple(pos, "title"), conn.SongTuple(pos, "artist"))
        ).strip()

        if not title:
            title = conn.SongTitle(pos)

        yield SongLeaf(pos, title)


def get_playlist_songs() -> ty.Iterator[SongLeaf]:
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
            yield SongLeaf(pos, nam)


def get_current_song() -> str | None:
    try:
        conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
        pos = conn.Position()
        total = conn.Length()
        info = "\n".join(
            filter(
                None,
                (
                    conn.SongTuple(pos, "title"),
                    conn.SongTuple(pos, "artist"),
                    conn.SongTitle(pos),
                    _("Position: %(pos)d / %(total)d")
                    % {"pos": pos, "total": total},
                ),
            )
        )
        return info
    except Exception:
        pretty.print_exc(__name__)

    with subprocess.Popen(
        [_AUDTOOL, "current-song"], stdout=subprocess.PIPE
    ) as proc:
        stdout, _stderr = proc.communicate()
        for line in stdout.splitlines():
            return kupferstring.fromlocale(line)

        return None


class Enqueue(Action):
    action_accelerator = "e"

    def __init__(self):
        Action.__init__(self, _("Enqueue"))

    def activate(self, leaf, iobj=None, ctx=None):
        pos = leaf.object
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.PlayqueneAdd(pos)
        except Exception:
            pretty.print_exc(__name__)
            launch.spawn_async((_AUDTOOL, "playqueue-add", str(pos)))

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
        pos = leaf.object
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.PlayqueneRemove(pos)
        except Exception:
            launch.spawn_async((_AUDTOOL, "playqueue-remove", str(pos)))

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
        pos = leaf.object
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Jump(pos)
            conn.Play()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playlist-jump", str(pos)))
            launch.spawn_async((_AUDTOOL, "playback-play"))

    def get_description(self):
        return _("Jump to track in Audacious")

    def get_icon_name(self):
        return "media-playback-start"


class Play(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Play"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Play()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playback-play"))

    def get_description(self):
        return _("Resume playback in Audacious")

    def get_icon_name(self):
        return "media-playback-start"


class Stop(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Stop"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Stop()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playback-play"))

    def get_description(self):
        return _("Stop playback in Audacious")

    def get_icon_name(self):
        return "media-playback-stop"


class Pause(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Pause"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Pause()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playback-pause"))

    def get_description(self):
        return _("Pause playback in Audacious")

    def get_icon_name(self):
        return "media-playback-pause"


class Next(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Next"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Advance()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playlist-advance"))

    def get_description(self):
        return _("Jump to next track in Audacious")

    def get_icon_name(self):
        return "media-skip-forward"


class Previous(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Previous"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.Reverse()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playlist-reverse"))

    def get_description(self):
        return _("Jump to previous track in Audacious")

    def get_icon_name(self):
        return "media-skip-backward"


class ClearQueue(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Clear Queue"))

    def run(self, ctx=None):
        try:
            conn = _create_dbus_connection(_IFACE_NAME, _OBJ_NAME, _BUS_NAME)
            conn.PlayqueneClear()
        except Exception:
            launch.spawn_async((_AUDTOOL, "playqueue-clear"))

    def get_description(self):
        return _("Clear the Audacious play queue")

    def get_icon_name(self):
        return "edit-clear"


class Shuffle(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Shuffle"))

    def run(self, ctx=None):
        launch.spawn_async((_AUDTOOL, "playlist-shuffle-toggle"))

    def get_description(self):
        return _("Toggle shuffle in Audacious")

    def get_icon_name(self):
        return "media-playlist-shuffle"


class Repeat(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Repeat"))

    def run(self, ctx=None):
        launch.spawn_async((_AUDTOOL, "playlist-repeat-toggle"))

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

    def get_text_representation(self):
        return self.name


class AudaciousSongsSource(Source):
    def __init__(self):
        Source.__init__(self, _("Playlist"))

    def get_items(self):
        try:
            yield from get_playlist_songs_dbus()
        except Exception:
            pretty.print_exc(__name__)
            yield from get_playlist_songs()

    def get_gicon(self):
        return icons.ComposedIcon(
            _AUDACIOUS, "audio-x-generic", emblem_is_fallback=True
        )

    def provides(self):
        yield SongLeaf


class AudaciousSource(AppLeafContentMixin, Source):
    appleaf_content_id = _AUDACIOUS
    source_user_reloadable = True
    source_scan_interval: int = 3600

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
        yield Stop()
        yield Pause()
        yield Next()
        yield Previous()
        yield ClearQueue()
        yield ShowPlaying()
        # Commented as these seem to have no effect
        # yield Shuffle()
        # yield Repeat()
        songs_source = AudaciousSongsSource()
        yield SourceLeaf(songs_source)
        if __kupfer_settings__["playlist_toplevel"]:
            yield from songs_source.get_leaves()

    def get_description(self):
        return __description__

    def get_icon_name(self):
        return _AUDACIOUS

    def provides(self):
        yield RunnableLeaf
