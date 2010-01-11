from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf
from kupfer.obj.contacts import ContactLeaf, email_from_leaf
from kupfer import utils

__kupfer_name__ = _("Default Email Client")
__kupfer_actions__ = ("NewMailAction", )
__description__ = _("Compose email using the system's default mailto: handler")
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class NewMailAction(Action):
	def __init__(self):
		Action.__init__(self, _('Compose New Mail'))

	def activate(self, leaf):
		email = email_from_leaf(leaf)
		utils.show_url("mailto:%s" % email)

	def item_types(self):
		yield ContactLeaf
		yield TextLeaf
		yield UrlLeaf
	def valid_for_item(self, item):
		return bool(email_from_leaf(item))

	def get_description(self):
		return __description__
	def get_icon_name(self):
		return "mail-message-new"
