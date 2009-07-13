from kupfer.objects import Action, TextLeaf, ActionDecorator
from kupfer import utils

__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_action_decorator__ = ("Decorator", )
__description__ = _("Send search queries to Wikipedia")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Decorator (ActionDecorator):
	def applies_to(self):
		yield TextLeaf
	def get_actions(self, leaf=None):
		return (WikipediaSearch(), )

class WikipediaSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search in Wikipedia"))

	def activate(self, leaf):
		from urllib import urlencode
		# Send in UTF-8 encoding
		search_url="http://en.wikipedia.org/w/index.php?title=Special:Search&go=Go"
		# will encode search=text, where `text` is escaped
		query_url = search_url + "&" + urlencode({"search": leaf.object})
		utils.show_url(query_url)
	def get_description(self):
		return _("Search for this term in en.wikipedia.org")
	def get_icon_name(self):
		return "gtk-find"

