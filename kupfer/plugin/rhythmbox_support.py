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

import sys
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
        self.sValue = ''
        self.entry_type = entry_type
        self.wanted_keys = wanted_keys and set(wanted_keys)
        self.entries = []
        self.entry = None

    def startElement(self, sName, attributes):
        if sName == "entry" and attributes["type"] == self.entry_type:
            self.fParsingTag = True
            self.entry = {}
        self.sValue = ''

    def characters(self, sData):
        self.sValue += sData

    def endElement(self,sName):
        if sName == 'entry':
            self.fParsingTag = False
            if self.entry:
                self.lSongs.append(self.entry)
            self.entry = None
        elif self.fParsingTag:
            if not self.wanted_keys or sName in self.wanted_keys:
                self.entry[sName]  = self.sValue

if __name__ == "__main__":
    print 'Parsing Rhythmbox'
    RHYTHMDB = os.path.expanduser('~/.local/share/rhythmbox/rhythmdb.xml')
    sRhythmboxFile = RHYTHMDB
    rbParser = make_parser()
    lSongs = []
    rbHandler = RhythmBoxHandler(lSongs, "song")
    rbParser.setContentHandler(rbHandler)
    rbParser.parse(sRhythmboxFile)
    for itm in lSongs[:10]:
        print itm
