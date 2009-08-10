#!/usr/bin/python

"""
Copyright (c) 2007 Tyler G. Hicks-Wright

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
from shutil import copyfile
from xml.sax import make_parser
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesNSImpl
from xml.sax.handler import ContentHandler

class iTunesTrack:
    def __init__(self):
        self.sTitle = ''
        self.sArtist = ''
        self.nRating = -1

    def __str__(self):
        return "Track = %s - SArtist = %s - Rating: %d" % (self.sTitle, self.sArtist, self.nRating)

class ITunesHandler(ContentHandler):
    def __init__(self):
        ContentHandler.__init__(self)
        self.fParsingTag = False
        self.sTag = ''
        self.sValue = ''
        self.lTracks = []
        self.itTrack = None

    def startElement(self, sName, attributes):
        if sName == 'key':
            self.fParsingTag = True

    def characters(self, sData):
        if self.fParsingTag:
            self.sTag = sData
            self.sValue = ''
        else: # could be multiple lines, so append sData.
            self.sValue = self.sValue + sData

    def endElement(self,sName):
        if sName == 'key':
            self.fParsingTag = False
        else:
            if self.sTag == 'Track ID':
                # start of a new track, so a new object
                # is needed.
                self.itTrack = iTunesTrack()
            elif self.sTag == 'Name' and self.itTrack:
                self.itTrack.sTitle = self.sValue
            elif self.sTag == 'Artist' and self.itTrack:
                self.itTrack.sArtist = self.sValue
            elif self.sTag == 'Rating' and self.itTrack:
                self.itTrack.nRating = int(self.sValue) / 20
                # assume this is all the data we need
                # so append the track object to our list
                # and reset our track object to None.
                self.lTracks.append(self.itTrack)
                self.itTrack = None

class Entry:
    def __init__(self, sType):
        """
        Class Entry
        Defines a Rhythmbox Library entry.

        sType: The type of the entry
        lData: A list of tuples, each of which contain
               a piece of data about an entry. For example,
                 <artist>The Beatles</artist> is encoded as
                 ('artist', 'The Beatles')
               The list is used instead of a dictionary to
               maintain the ordering of data.
        """
        self.sType = sType
        self.lData = []

    def addData(self, sName, sData):
        self.lData.append((sName, sData))

class RhythmBoxHandler(ContentHandler):
    def __init__(self, dSongs):
        ContentHandler.__init__(self)
        self.dSongs = dSongs
        self.fParsingTag = False
        self.sValue = ''
        self.sTitle = ''
        self.sArtist = ''
        self.entries = []
        self.entry = None
        
    def startElement(self, sName, attributes):
        if sName == "entry":
            self.fParsingTag = True
            self.entry = Entry(attributes["type"])
        self.sValue = ''

    def characters(self, sData):
        self.sValue += sData

    def endElement(self,sName):
        if sName == 'entry':
            self.fParsingTag = False
            self.sTitle = ''
            self.sArtist = ''
            if len(self.entry.lData) > 0:
                self.entries.append(self.entry)
            self.entry = None
        elif self.fParsingTag:
            if sName == 'title':
                self.sTitle = self.sValue
            elif sName == 'artist':
                self.sArtist = self.sValue
            elif sName == 'rating':
                sKey = "%s - %s" % (self.sArtist, self.sTitle)
                if self.dSongs.has_key(sKey):
                    self.entry.addData('rating', str(self.dSongs[sKey]))
                else:
                    self.entry.addData('rating', self.sValue)
            if sName != "rating": # We've already added rating
                self.entry.addData(sName, self.sValue)

class RhythmDBWriter:
    def __init__(self, sFilesName, sEncoding):
        fOut = open(sFilesName, 'w')
        gen = XMLGenerator(fOut, sEncoding)
        gen.startDocument()
        self.gen = gen
        self.fOut = fOut
        attr_vals = {(None, u'version'): u'1.3',}
        attr_qsNames = {(None, u'version'): u'version',}
        xmlAttrs = AttributesNSImpl(attr_vals, attr_qsNames)
        self.gen.startElementNS((None, u'rhythmdb'), u'rhythmdb', xmlAttrs)
        self.fOut.write("\n")

    def writeEntry(self, entry):
        xmlAttrs = AttributesNSImpl({(None, u'type'): entry.sType,}, {(None, u'type'): u'type',})
        self.fOut.write("  ")
        self.gen.startElementNS((None, u'entry'), u'entry', xmlAttrs)
        self.fOut.write("\n")
        xmlAttrs = AttributesNSImpl({}, {})
        for p in entry.lData:
            self.fOut.write("    ")
            self.gen.startElementNS((None, p[0]), p[0], {})
            self.gen.characters(p[1])
            self.gen.endElementNS((None, p[0]), p[0])
            self.fOut.write("\n")
        self.fOut.write("  ")
        self.gen.endElementNS((None, u'entry'), u'entry')
        self.fOut.write("\n")

    def close(self):
        self.gen.endElementNS((None, u'rhythmdb'), u'rhythmdb')
        self.gen.endDocument()
        try:
            self.fOut.write("\n")
            self.fOut.close()
        except:
            pass

RHYTHMDB = '%s/.gnome2/rhythmbox/rhythmdb.xml' % (os.environ['HOME'],)
USAGE = """Usage: %s iTunesLibraryFile [RhythmboxLibraryFile]

%s copies your iTunes ratings into your Rythmbox library.
To ensure nothing is lost, a backup of your Rhythmbox
Library will be made.  It is recommended that you quit
Rhythmbox before running this script.

Arguments:
  iTunesLibraryFile - This file is usually:
    {Music Folder}/iTunes/iTunes Music Library.xml

  RhythmboxLibraryFile [optional] - Usually found at:
    %s
  If this argument is not specified, the default location
  will be used instead."""

def main(argv):
    if argv == None:
        argv = sys.argv
    if len(argv) < 2 or len(argv) > 3 or argv[1][0] == '-':
        sScriptName = argv[0][argv[0].rfind('/')+1:]
        print USAGE % (sScriptName, sScriptName, RHYTHMDB)
        return
    siTunesFile = argv[1]
    if len(argv) == 3:
        sRhythmboxFile = argv[2]
    else:
        sRhythmboxFile = RHYTHMDB
    sRhythmboxBackup = sRhythmboxFile + ".bak"

    try:
        print "Backing up Rhythmbox Library"
        copyfile(sRhythmboxFile, sRhythmboxBackup)
    except:
        print "Could not back up Rhythmbox Library from %s to %s." % (sRhythmboxFile, sRhythmboxBackup)
        return

    try:    
        print "Parsing iTunes"
        parser = make_parser()
        handler = ITunesHandler()
        parser.setContentHandler(handler)
        parser.parse(siTunesFile)
    except:
        print >> sys.stderr, "Could not parse iTunes file %s" % siTunesFile
        return

    try:
        print 'Populating Song Data'
        dSongs = {}
        for track in handler.lTracks:
            dSongs["%s - %s" % (track.sArtist, track.sTitle)] = track.nRating
        print 'Parsing Rhythmbox'
        rbParser = make_parser()
        rbHandler = RhythmBoxHandler(dSongs)
        rbParser.setContentHandler(rbHandler)
        rbParser.parse(sRhythmboxFile)
    except:
        print >> sys.stderr, "Could not parse Rhythmbox Library: %s" % sRhythmboxFile
        return

    try:
        print "Outputting Data"
        rdw = RhythmDBWriter(sRhythmboxFile, "utf-8")
        for song in rbHandler.entries:
            rdw.writeEntry(song)
        print "Done"
    except:
        rdw.fOut.close()
        print >> sys.stderr, "Failed to write new library.  Restoring from backup..."
        try:
            copyfile(sRhythmboxBackup, sRhythmboxFile)
        except:
            print >> sys.stderr, "Could not automatically resore backup.  Please manually restore from %s" % sRhythmboxBackup
        print >> sys.stderr, "Backup restored."
    finally:
        rdw.close()

if __name__ == "__main__":
    main(sys.argv)
