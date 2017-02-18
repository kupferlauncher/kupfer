"""
This is a simple plugin demonstration, how to add single, simple actions
"""

__kupfer_name__ = _("Wikipedia")
__kupfer_sources__ = ()
__kupfer_actions__ = ("WikipediaSearch", )
__description__ = _("Search in Wikipedia")
__version__ = "2017.1"
__author__ = "US"

import urllib.parse

from kupfer.objects import Action, TextLeaf
from kupfer import utils, plugin_support


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "lang",
        "label": _("Wikipedia language"),
        "type": str,
        # TRANS: Default wikipedia language code
        "value": _("en"),
    },
)


class WikipediaSearch (Action):
    def __init__(self):
        Action.__init__(self, _("Search in Wikipedia"))

    def activate(self, leaf):
        # Send in UTF-8 encoding
        lang_code = __kupfer_settings__["lang"]
        search_url="https://%s.wikipedia.org/w/index.php?title=Special:Search&go=Go" % lang_code
        # will encode search=text, where `text` is escaped
        query_url = search_url + "&" + urllib.parse.urlencode({"search": leaf.object})
        utils.show_url(query_url)
    def item_types(self):
        yield TextLeaf
    def get_description(self):
        lang_code = __kupfer_settings__["lang"]
        return _("Search for this term in %s.wikipedia.org") % lang_code
    def get_icon_name(self):
        return "edit-find"

