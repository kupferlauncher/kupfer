"""
This is a DuckDuckGo search plugin initially modified from the Wikipedia search 
plugin
"""

__kupfer_name__ = _("DuckDuckGo HTTPS Search")
__kupfer_sources__ = ()
__kupfer_actions__ = ("DuckDuckGoSearch",)
__description__ = _("Search securely with DuckDuckGo")
__version__ = "0.1"
__author__ = "Isaac Aggrey <isaac.aggrey@gmail.com>"

import urllib

from kupfer.objects import Action, TextLeaf
from kupfer import utils, plugin_support

class DuckDuckGoSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search securely with DuckDuckGo"))

	def activate(self, leaf):
		search_url="https://duckduckgo.com/" 
		query_url = search_url + "&" + urllib.urlencode({"q" : leaf.object})
		utils.show_url(query_url)

	def item_types(self):
		yield TextLeaf

	def get_description(self):
		return _("Search securely for this term in DuckDuckGo")

	def get_icon_name(self):
		return "edit-find"
