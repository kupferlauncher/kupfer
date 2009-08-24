
from xml.sax.handler import ContentHandler

class XMLEntryHandler(ContentHandler):
    """Parse XML input into a list of dictionaries.
    Get only entries of type @entry_type are taken.
    and only record keys in the iterable wanted_keys.

    This ContentHandler keeps a big string mapping open, to
    make sure that equal strings are using equal instances to save memory.
    """
    def __init__(self, entries, entry_name, entry_attributes, wanted_keys):
        ContentHandler.__init__(self)
        self.all_entries = entries
        self.entry_name = entry_name
        self.entry_attributes = entry_attributes.items()
        self.wanted_keys = dict((k, k) for k in wanted_keys)
        self.is_parsing_tag = False
        self.is_wanted_element = False
        self.song_entry = None
        self.string_map = {}
        self.element_content = ''

    def startElement(self, sName, attributes):
        if (sName == self.entry_name and
                all(attributes.get(k) == v for k, v in self.entry_attributes)):
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
        if sName == self.entry_name:
            if self.song_entry:
                self.all_entries.append(self.song_entry)
            self.song_entry = None
            self.is_parsing_tag = False
        elif self.is_parsing_tag and self.is_wanted_element:
            sName = self.wanted_keys[sName]
            self.song_entry[sName] = self._get_or_internalize(self.element_content)
