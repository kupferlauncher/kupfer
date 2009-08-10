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

if __name__ == "__main__":
    main(sys.argv)
