__kupfer_name__ = _("Google Search")
__kupfer_actions__ = ("GoogleSearch", )
__description__ = _("Search Google with results shown in browser")
__version__ = ""
__author__ = "thorko"

import http.client
import urllib.parse

from kupfer.objects import Action, TextLeaf
from kupfer import utils

class GoogleSearch (Action):
    def __init__(self):
        Action.__init__(self, _("Google Search"))

    def activate(self, leaf):
        search_url = "https://www.google.com/search"
        query_url = search_url + "?" + urllib.parse.urlencode({"q": leaf.object})
        utils.show_url(query_url)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search the web with google.com")

    def get_icon_name(self):
        return "edit-find"

