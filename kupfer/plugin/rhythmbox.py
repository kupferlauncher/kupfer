__kupfer_name__ = _("Rhythmbox")
__kupfer_sources__ = ("RhythmboxSource", )
__description__ = _("Play and enqueue tracks and browse the music library")
__version__ = "2017.2"
__author__ = "US, Karol Będkowski"

'''
Changes:
    2012-10-17 Karol Będkowski:
        + control rhythmbox via dbus interface
        + load songs via dbus interface
'''


import itertools
from hashlib import md5

from gi.repository import Gio
import os

import dbus

from kupfer import pretty
from kupfer.objects import Leaf, Source, Action, RunnableLeaf, SourceLeaf
from kupfer.objects import FileLeaf
from kupfer import icons, utils, config
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer.objects import OperationError, NotAvailableError
from kupfer.weaklib import dbus_signal_connect_weakly
from kupfer import plugin_support

from kupfer.plugin import rhythmbox_support

plugin_support.check_dbus_connection()

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

_BUS_NAME = 'org.gnome.Rhythmbox3'
_OBJ_PATH_MPRIS = '/org/mpris/MediaPlayer2'
_OBJ_NAME_MPRIS_PLAYER = 'org.mpris.MediaPlayer2.Player'
_OBJ_PATH_MEDIASERVC_ALL = '/org/gnome/UPnP/MediaServer2/Library/all'
_OBJ_NAME_MEDIA_CONT = 'org.gnome.UPnP.MediaContainer2'


def _tostr(ustr):
    return ustr

def _toutf8_lossy(ustr):
    return ustr.encode("UTF-8", "replace")

def _create_dbus_connection_mpris(obj_name, obj_path, activate=False):
    ''' Create dbus connection to Rhytmbox
        @activate: if True, start program if not running
    '''
    interface = None
    sbus = dbus.SessionBus()
    try:
        proxy_obj = sbus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        if activate or dbus_iface.NameHasOwner(_BUS_NAME):
            obj = sbus.get_object(_BUS_NAME, obj_path)
            if obj:
                interface = dbus.Interface(obj, obj_name)
    except dbus.exceptions.DBusException as err:
        pretty.print_debug(err)
    return interface

def _canonicalize(strmap, string):
    """Look up @string in the string map,
    and return the copy in the map.

    If not found, update the map with the string.
    """
    try:
        return strmap[string]
    except KeyError:
        string = str(string)
        strmap[string] = string
        return string

def _tracknr(string):
    try:
        return int(string)
    except ValueError:
        return None

def _get_all_songs_via_dbus():
    iface = _create_dbus_connection_mpris(_OBJ_NAME_MEDIA_CONT,
            _OBJ_PATH_MEDIASERVC_ALL)
    if iface:
        ss = {}
        for item in iface.ListItems(0, 9999, ['*']):
            yield {
                'album': _canonicalize(ss, item['Album']),
                    'artist': _canonicalize(ss, item['Artist']),
                    'title': str(item['DisplayName']),
                    'track-number': _tracknr(item['TrackNumber']),
                    'location': str(item['URLs'][0]),
                    'date': _canonicalize(ss, item['Date']),
                }

def spawn_async(argv):
    try:
        utils.spawn_async_raise(argv)
    except utils.SpawnError as exc:
        raise OperationError(exc)

def enqueue_songs(info, clear_queue=False, play_first=False):
    songs = list(info)
    if not songs:
        return
    qargv = ["rhythmbox-client"]
    if clear_queue:
        qargv.append("--clear-queue")
    if play_first and songs:
        song = songs[0]
        songs = songs[1:]
        uri = _tostr(song["location"])
        qargv.append("--play-uri")
        qargv.append(uri)
    for song in songs:
        uri = _tostr(song["location"])
        qargv.append("--enqueue")
        qargv.append(uri)
    spawn_async(qargv)

class ClearQueue (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Clear Queue"))
    def run(self):
        spawn_async(("rhythmbox-client", "--no-start", "--clear-queue"))
    def get_icon_name(self):
        return "edit-clear"

def _songs_from_leaf(leaf):
    "return a sequence of songs from @leaf"
    if isinstance(leaf, SongLeaf):
        return (leaf.object, )
    if isinstance(leaf, TrackCollection):
        return list(leaf.object)

class PlayTracks (Action):
    action_accelerator = "o"

    rank_adjust = 5
    def __init__(self):
        Action.__init__(self, _("Play"))

    def activate(self, leaf):
        self.activate_multiple((leaf, ))

    def activate_multiple(self, objects):
        # for multiple dispatch, play the first and enqueue the rest
        to_enqueue = []
        for leaf in objects:
            to_enqueue.extend(_songs_from_leaf(leaf))
        if to_enqueue:
            enqueue_songs(to_enqueue,
                          clear_queue=len(to_enqueue) > 1,
                          play_first=True)

    def get_description(self):
        return _("Play tracks in Rhythmbox")
    def get_icon_name(self):
        return "media-playback-start"

class Enqueue (Action):
    action_accelerator = "e"

    def __init__(self):
        Action.__init__(self, _("Enqueue"))
    def activate(self, leaf):
        self.activate_multiple((leaf, ))

    def activate_multiple(self, objects):
        to_enqueue = []
        for leaf in objects:
            to_enqueue.extend(_songs_from_leaf(leaf))
        enqueue_songs(to_enqueue)

    def get_description(self):
        return _("Add tracks to the play queue")
    def get_gicon(self):
        return icons.ComposedIcon("gtk-execute", "media-playback-start")
    def get_icon_name(self):
        return "media-playback-start"

class SongLeaf (Leaf):
    serializable = 1
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
        yield GetFile()
    def get_description(self):
        # TRANS: Song description
        return _("by %(artist)s from %(album)s") % {
                "artist": self.object["artist"],
                "album": self.object["album"],
                }
    def get_icon_name(self):
        return "audio-x-generic"

class GetFile (Action):
    def __init__(self):
        super().__init__(_("Get File"))

    def has_result(self):
        return True

    def activate(self, leaf):
        gfile = Gio.File.new_for_uri(leaf.object["location"])
        try:
            path = gfile.get_path()
        except Exception as exc:
            # On utf-8 decode error
            # FIXME: Unrepresentable path
            raise OperationError(exc)
        if path:
            result = FileLeaf(path)
            if result.is_valid():
                return result
        raise NotAvailableError(str(leaf))

class CollectionSource (Source):
    def __init__(self, leaf):
        Source.__init__(self, str(leaf))
        self.leaf = leaf
    def get_items(self):
        for song in self.leaf.object:
            yield SongLeaf(song)
    def repr_key(self):
        return self.leaf.repr_key()
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

    def _get_thumb_local(self):
        # try local filesystem
        uri = self.object[0]["location"]
        artist = self.object[0]["artist"].lower()
        album = self.object[0]["album"].lower()
        gfile = Gio.File.new_for_uri(uri)
        cdir = gfile.resolve_relative_path("../").get_path()
        # We don't support unicode ATM
        bs_artist_album = \
            " - ".join([artist, album])
        bs_artist_album2 = \
            "-".join([artist, album])
            #" - ".join([us.encode("ascii", "ignore") for us in (artist, album)])
        cover_names = (
                "cover.jpg", "album.jpg", "albumart.jpg",
                "cover.gif", "album.png",
                ".folder.jpg", "folder.jpg",
                bs_artist_album + ".jpg",
                bs_artist_album2 + ".jpg",
            )
        try:
            for cover_name in os.listdir(cdir):
                if cover_name.lower() in cover_names:
                    cfile = gfile.resolve_relative_path("../" + cover_name)
                    return cfile.get_path()
        except OSError:
            pretty.print_exc(__name__)
            return None

    def _get_thumb_mediaart(self):
        """old thumb location"""
        ltitle = str(self).lower()
        # ignore the track artist -- use the space fallback
        # hash of ' ' as fallback
        hspace = "7215ee9c7d9dc229d2921a40e899ec5f"
        htitle = md5(_toutf8_lossy(ltitle)).hexdigest()
        hartist = hspace
        cache_name = "album-%s-%s.jpeg" % (hartist, htitle)
        return config.get_cache_file(("media-art", cache_name))


    def get_thumbnail(self, width, height):
        if not hasattr(self, "cover_file"):
            self.cover_file = (self._get_thumb_mediaart() or
                               self._get_thumb_local())
        return icons.get_pixbuf_from_file(self.cover_file, width, height)

class ArtistAlbumsSource (CollectionSource):
    def get_items(self):
        albums = {}
        for song in self.leaf.object:
            album = song["album"]
            album_list = albums.get(album, [])
            album_list.append(song)
            albums[album] = album_list
        names = utils.locale_sort(albums)
        names.sort(key=lambda name: albums[name][0]['date'])
        for album in names:
            yield AlbumLeaf(albums[album], album)
    def should_sort_lexically(self):
        return False

class ArtistLeaf (TrackCollection):
    def get_description(self):
        # TRANS: Artist songs collection description
        return _("Tracks by %s") % (str(self), )
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
    """Locale sort dictionary @artists by Artist, then Album;
    each artist in @artists should already contain songs
    grouped by album and sorted by track number.
    """
    for artist in utils.locale_sort(artists):
        artist_songs = artists[artist]
        albums = {}
        albumkey = lambda song: song["album"]
        for album, songs in itertools.groupby(artist_songs, albumkey):
            albums.setdefault(album, []).extend(songs)
        for album in utils.locale_sort(albums):
            for song in albums[album]:
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

class RhythmboxSource (AppLeafContentMixin, Source, PicklingHelperMixin):
    appleaf_content_id = "rhythmbox"
    def __init__(self):
        super().__init__(_("Rhythmbox"))
        self._version = 3
        self._songs = []

    def initialize(self):
        bus = dbus.SessionBus()
        dbus_signal_connect_weakly(bus, "NameOwnerChanged", self._name_owner_changed,
                                   dbus_interface="org.freedesktop.DBus",
                                   arg0=_BUS_NAME)

    def _name_owner_changed(self, name, old, new):
        if new:
            self.mark_for_update()

    def pickle_prepare(self):
        self.mark_for_update()

    def get_items(self):
        # first try to load songs via dbus
        songs = list(_get_all_songs_via_dbus())
        self._songs = songs = songs or self._songs
        albums = rhythmbox_support.parse_rhythmbox_albums(songs)
        artists = rhythmbox_support.parse_rhythmbox_artists(songs)
        yield ClearQueue()
        artist_source = RhythmboxArtistsSource(artists)
        album_source = RhythmboxAlbumsSource(albums)
        songs_source = RhythmboxSongsSource(artists)
        yield SourceLeaf(artist_source)
        yield SourceLeaf(album_source)
        yield SourceLeaf(songs_source)
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
