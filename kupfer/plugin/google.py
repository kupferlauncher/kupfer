import gobject

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf, ActionDecorator
from kupfer import utils


__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_action_decorator__ = ("GoogleDecorator", )
__description__ = _("Send search queries to Google")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class GoogleDecorator (ActionDecorator):
	"""Base class for an object assigning more actions to Leaves"""
	def applies_to(self):
		yield TextLeaf
	def get_actions(self, leaf=None):
		return (GoogleSearch(), )

class GoogleSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search with Google"))

	def activate(self, leaf):
		# Replace & in query
		search_string = leaf.object.replace("&", "&amp;")
		# Send in UTF-8 encoding
		search_url = "http://www.google.com/search?ie=utf-8&q=%s"
		query_url = search_url % search_string
		utils.show_url(query_url)
	def get_description(self):
		return _("Open google.com and search for this term")
	def get_icon_name(self):
		return "gtk-find"

