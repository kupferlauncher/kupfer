"""
This is a DuckDuckGo search plugin based on the Wikipedia search plugin
"""

__kupfer_name__ = _("DuckDuckGo Search")
__kupfer_sources__ = ()
__kupfer_actions__ = ("DuckDuckGoSearch",)
__description__ = _("Search the web securely with DuckDuckGo")
__version__ = "1.0"
__author__ = "Isaac Aggrey <isaac.aggrey@gmail.com>"

import urllib.parse

from kupfer.objects import Action, TextLeaf
from kupfer import utils

class DuckDuckGoSearch (Action):
    def __init__(self):
        Action.__init__(self, _("DuckDuckGo Search"))

    def activate(self, leaf):
        search_url = "https://duckduckgo.com/"
        query_url = search_url + "?" + urllib.parse.urlencode({"q" : leaf.object})
        utils.show_url(query_url)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search the web securely with DuckDuckGo")

    def get_icon_name(self):
        return "edit-find"
