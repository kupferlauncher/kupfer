""" ID2 – Guess Identifier (Kupfer Plugin). See https://id2.dev
"""
__kupfer_name__ = _("Identifier Resolver")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("IdentifierSource", )
__kupfer_actions__ = ("LookupID", )
__description__ = _("""Detect and open DOIs, ISBNs, OrcIDs, crypto-addresses, geo-coordinates, and more in your web-browser. Examples:

- Unicode:  \t"U+1F194"
- UnixTime: \t"1606324253"
- Location: \t"8FWH4HX8+QR"
- DOI:    \t\t"10.1109/FDL.2018.8524068"
- OrcID:    \t"0000-0002-0006-7761"
- BitCoin:  \t"3FZbgi29cpjq2GjdwV8eyHuJJnkLtktZc5"

For a full list, see https://id2.dev

To disable a certain ID, write a single character (e.g. "x") into the URL field below.
""")
__version__ = "2021.0"
__author__ = "Emanuel Regnath"


from kupfer.plugin.id2_support import id2data   # Dict/JSON with all IDs
from kupfer import utils, plugin_support
from kupfer.objects import Action, TextLeaf, TextSource
import re
import urllib.parse


# global table holding identifier classes and icon names
CLASS_NAMES = {
    "i": ["Identifier", "edit-find"],
    "g": ["Geo-Location", "applications-internet"],
    "d": ["Document", "x-office-document"],
    "o": ["Object", "package-x-generic"],
    "h": ["Hash", "dialog-password"],
    "t": ["Time", "x-office-calendar"],
    "w": ["Person", "stock_person"],
}


# kupfer setting keys must not have colons
def _settings_key(key: str):
    return key.replace(':', '_')


# keys for which we allow custom URLs via Settings
# these should be IDs with multiple resolvers.
SETTING_URL_KEYS = ["i:ip4", "i:ip6", "i:utf8",
                    "g:gps", "o:ean", "o:upc", "o:asin"]

__kupfer_settings__ = plugin_support.PluginSettings(
    *[{"key": _settings_key(k),
       "label": "URL for "+k[2:].upper(),
       "type": str,
       "value": id2data[k]["url"]} for k in SETTING_URL_KEYS if k in id2data]
)


def guess_id(token: str):
    """Test if "token" matches the regex of any identifier and return all found types."""
    token = token.strip()
    types = []
    for key, entry in id2data.items():
        if key in SETTING_URL_KEYS and len(__kupfer_settings__[_settings_key(key)]) < 3:
            continue
        if len(token) in entry["lens"]:
            match = re.match(r'^'+entry["re"]+r'$', token)
            if match:
                entry["part"] = match.group(1)
                types.append(entry)
    return types


def _parse_identifier_lengths():
    """parse "len" key string and assign a list of integers to speed up execution"""
    lens = []
    for key, entry in id2data.items():
        parts = entry['len'].split(",")
        for part in parts:
            nums = part.split("-")
            imin = int(nums[0])
            if(len(nums) == 2):
                if(nums[1] == ""):
                    nums[1] = "40"
                imax = int(nums[1])
                lens = list(range(imin, imax+1))
            else:
                lens.append(imin)

        id2data[key]['lens'] = lens


class IdentifierLeaf(TextLeaf):
    def __init__(self, id2key, token):
        TextLeaf.__init__(self, token)
        self.id2key = id2key
        self.id2cls = id2key[0]

    def get_actions(self):
        yield LookupID()

    def get_icon_name(self):
        return CLASS_NAMES[self.id2cls][1]

    def get_description(self):
        return "{} ID: {}".format(CLASS_NAMES[self.id2cls][0],
                                  id2data[self.id2key]["desc"])


class IdentifierSource(TextSource):
    def __init__(self):
        TextSource.__init__(self, name=_('ID2 Identifiers'))

    def get_text_items(self, text):
        if len(text) < 5:
            return None
        types = guess_id(text)
        for entry in types:
            yield IdentifierLeaf(entry['id'], text)

    def provides(self):
        yield IdentifierLeaf

    def get_rank(self):
        return 42


class LookupID (Action):
    def __init__(self):
        Action.__init__(self, name=_("Open in Browser"))
        self.rank_adjust = 5  # default action for IdentifierLeaf

    def activate(self, leaf):
        """Called when item is selected via Enter/click"""
        entry = id2data[leaf.id2key]
        if leaf.id2key in SETTING_URL_KEYS:
            url_prefix = __kupfer_settings__[_settings_key(leaf.id2key)]
        else:
            url_prefix = entry["url"]
        utils.show_url(url_prefix + entry["part"])

    def item_types(self):
        yield IdentifierLeaf

    def get_description(self):
        return _("Resolve this ID using a WebService")

    def get_icon_name(self):
        return "web-browser"


def initialize_plugin(name):
    _parse_identifier_lengths()
