"""
This is a simple plugin demonstration, how to add single, simple actions
"""

import urllib

from kupfer.objects import Action, TextLeaf
from kupfer import utils

__kupfer_name__ = _("Wikipedia")
__kupfer_sources__ = ()
__kupfer_actions__ = ("WikipediaSearch", )
__description__ = _("Send search queries to Wikipedia")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class WikipediaSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Wikipedia"))

	def activate(self, leaf):
		# Send in UTF-8 encoding
		search_url="http://en.wikipedia.org/w/index.php?title=Special:Search&go=Go"
		# will encode search=text, where `text` is escaped
		query_url = search_url + "&" + urllib.urlencode({"search": leaf.object})
		utils.show_url(query_url)
	def item_types(self):
		yield TextLeaf
	def get_description(self):
		return _("Search for this term in en.wikipedia.org")
	def get_icon_name(self):
		return "gtk-find"

