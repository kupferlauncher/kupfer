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
    """
    def __init__(self, lSongs, entry_type, wanted_keys=None):
        ContentHandler.__init__(self)
        self.lSongs = lSongs
        self.fParsingTag = False
        self.fWantElement = False
        self.sValue = ''
        self.entry_type = entry_type
        self.wanted_keys = wanted_keys and set(wanted_keys)
        self.entries = []
        self.entry = None

    def startElement(self, sName, attributes):
        if sName == "entry" and attributes["type"] == self.entry_type:
            self.fParsingTag = True
            self.entry = {}
            self.fWantElement = True
        elif not self.wanted_keys or sName in self.wanted_keys:
            self.fWantElement = True
        else:
            self.fWantElement = False
        self.sValue = ''

    def characters(self, sData):
        if self.fWantElement:
            self.sValue += sData

    def endElement(self,sName):
        if sName == 'entry':
            self.fParsingTag = False
            if self.entry:
                self.lSongs.append(self.entry)
            self.entry = None
        elif self.fParsingTag and self.fWantElement:
            self.entry[sName]  = self.sValue

NEEDED_KEYS= ("title", "artist", "album", "track-number", "location", )
def get_rhythmbox_songs(typ="song", keys=None, dbfile='~/.local/share/rhythmbox/rhythmdb.xml'):
    sRhythmboxFile = os.path.expanduser(dbfile)
    rbParser = make_parser()
    lSongs = []
    rbHandler = RhythmBoxHandler(lSongs, typ, keys)
    rbParser.setContentHandler(rbHandler)
    rbParser.parse(sRhythmboxFile)
    return lSongs

def get_rhythmbox_albums(dbfile='~/.local/share/rhythmbox/rhythmdb.xml'):
    songs = get_rhythmbox_songs(keys=NEEDED_KEYS, dbfile=dbfile)
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
    def get_track_number(rec):
        tnr = rec.get("track-number")
        if not tnr: return None
        try:
            tnr = int(tnr)
        except ValueError:
            pass
        return tnr
    # sort album in track order
    for album in albums:
        albums[album].sort(key=get_track_number)
    return albums

if __name__ == "__main__":
    for rec in get_rhythmbox_artist_albums().itervalues():
        print rec
        break
