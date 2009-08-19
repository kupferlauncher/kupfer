#!/usr/bin/python

"""
Copyright (c) 2007 Tyler G. Hicks-Wright
              2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os
from xml.sax import make_parser
from xml.sax.saxutils import XMLGenerator
from xml.sax.handler import ContentHandler

class RhythmBoxHandler(ContentHandler):
    """Parse rhythmbox library into a list of dictionaries.
    Get only entries of type @entry_type (commonly "song"),
    and only record keys in the iterable wanted_keys, or all
    if None.

    This ContentHandler keeps a big string mapping open, to
    make sure that equal strings are using equal instances to save memory
    """
    def __init__(self, songs, entry_type, wanted_keys):
        ContentHandler.__init__(self)
        self.all_entries = songs
        self.entry_type = entry_type
        self.wanted_keys = dict((k, k) for k in wanted_keys)
        self.is_parsing_tag = False
        self.is_wanted_element = False
        self.song_entry = None
        self.string_map = {}
        self.element_content = ''

    def startElement(self, sName, attributes):
        if sName == "entry" and attributes["type"] == self.entry_type:
            self.song_entry = {}
            self.is_parsing_tag = True
            self.is_wanted_element = True
        else:
            self.is_wanted_element = (sName in self.wanted_keys)
        self.element_content = ''

    def characters(self, sData):
        if self.is_wanted_element:
            self.element_content += sData

    def _get_or_internalize(self, string):
        if string not in self.string_map:
            self.string_map[string] = string
            return string
        return self.string_map[string]

    def endElement(self,sName):
        if sName == 'entry':
            if self.song_entry:
                self.all_entries.append(self.song_entry)
            self.song_entry = None
            self.is_parsing_tag = False
        elif self.is_parsing_tag and self.is_wanted_element:
            sName = self.wanted_keys[sName]
            self.song_entry[sName] = self._get_or_internalize(self.element_content)

NEEDED_KEYS= ("title", "artist", "album", "track-number", "location", )
def get_rhythmbox_songs(typ="song", keys=NEEDED_KEYS,
        dbfile='~/.local/share/rhythmbox/rhythmdb.xml'):
    rhythmbox_dbfile = os.path.expanduser(dbfile)
    rbParser = make_parser()
    lSongs = []
    rbHandler = RhythmBoxHandler(lSongs, typ, keys)
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

