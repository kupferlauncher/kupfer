from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf, FileLeaf
from kupfer.obj.contacts import ContactLeaf, email_from_leaf
from kupfer import utils

__kupfer_name__ = _("Default Email Client")
__kupfer_actions__ = (
	"NewMailAction",
	"SendFileByMail",
)
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

class SendFileByMail (Action):
	def __init__(self):
		Action.__init__(self, _('Send by Email To..'))

	def activate(self, obj, iobj):
		filepath = obj.object
		email = email_from_leaf(iobj)
		# FIXME: revisit for unicode email addresses
		url = "mailto:%s?attach=%s" % (email, filepath)
		utils.show_url(url)

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return not item.is_dir()

	def requires_object(self):
		return True
	def object_types(self):
		yield ContactLeaf
		yield TextLeaf
		yield UrlLeaf
	def valid_object(self, iobj, for_item=None):
		return bool(email_from_leaf(iobj))

	def get_icon_name(self):
		return "document-send"
