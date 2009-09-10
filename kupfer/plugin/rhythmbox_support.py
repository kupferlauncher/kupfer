
import os
import xml.sax

from . import xml_support

NEEDED_KEYS= ("title", "artist", "album", "track-number", "location", )

def get_rhythmbox_songs(typ="song", keys=NEEDED_KEYS,
        dbfile='~/.local/share/rhythmbox/rhythmdb.xml'):
    if not dbfile or not os.path.exists(dbfile):
        raise IOError("Rhythmbox database not found")
    rhythmbox_dbfile = os.path.expanduser(dbfile)
    rbParser = xml.sax.make_parser()
    lSongs = []
    attributes = {"type": typ}
    rbHandler = xml_support.XMLEntryHandler(lSongs, "entry", attributes, keys)
    rbParser.setContentHandler(rbHandler)
    rbParser.parse(rhythmbox_dbfile)
    return lSongs

def sort_album(album):
    """Sort album in track order"""
    def get_track_number(rec):
        tnr = rec.get("track-number")
        if not tnr: return None
        try:
            tnr = int(tnr)
        except ValueError:
            pass
        return tnr
    album.sort(key=get_track_number)

def sort_album_order(songs):
    """Sort songs in order by album then by track number

    >>> songs = [
    ... {"title": "a", "album": "B", "track-number": "2"},
    ... {"title": "b", "album": "A", "track-number": "1"},
    ... {"title": "c", "album": "B", "track-number": "1"},
    ... ]
    >>> sort_album_order(songs)
    >>> [s["title"] for s in songs]
    ['b', 'c', 'a']
    """
    def get_album_order(rec):
        tnr = rec.get("track-number")
        if not tnr: return None
        try:
            tnr = int(tnr)
        except ValueError:
            pass
        return (rec["album"], tnr)
    songs.sort(key=get_album_order)

def parse_rhythmbox_albums(songs):
    albums = {}
    for song in songs:
        song_artist = song["artist"]
        if not song_artist:
            continue
        song_album = song["album"]
        if not song_album:
            continue
        album = albums.get(song_album, [])
        album.append(song)
        albums[song_album] = album
    # sort album in track order
    for album in albums:
        sort_album(albums[album])
    return albums

def parse_rhythmbox_artists(songs):
    artists = {}
    for song in songs:
        song_artist = song["artist"]
        if not song_artist:
            continue
        artist = artists.get(song_artist, [])
        artist.append(song)
        artists[song_artist] = artist
    # sort in album + track order
    for artist in artists:
        sort_album_order(artists[artist])
    return artists

