import gobject

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf
from kupfer import utils


__kupfer_name__ = _("Search the Web")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("GoogleSearch", )
__description__ = _("Send search queries to Google")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class GoogleSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search with Google"))

	def activate(self, leaf):
		from urllib import urlencode
		search_url = "http://www.google.com/search?"
		# will encode search=text, where `text` is escaped
		query_url = search_url + urlencode({"q": leaf.object, "ie": "utf-8"})
		utils.show_url(query_url)
	def get_description(self):
		return _("Search for this term with Google")
	def get_icon_name(self):
		return "gtk-find"
	def item_types(self):
		yield TextLeaf

