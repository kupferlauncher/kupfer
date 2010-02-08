__kupfer_name__ = _("Default Email Client")
__description__ = _("Compose email using the system's default mailto: handler")
__kupfer_actions__ = (
	"NewMailAction",
	"SendFileByMail",
)
__kupfer_category__ = ("communication", )
__version__ = "2010-01-12"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf, FileLeaf
from kupfer.obj.contacts import ContactLeaf, email_from_leaf
from kupfer import utils, plugin_support


class NewMailAction(Action):
	def __init__(self):
		Action.__init__(self, _('Compose Email'))

	def activate(self, leaf):
		email = email_from_leaf(leaf)
		utils.show_url("mailto:%s" % email)

	def activate_multiple(self, objects):
		recipients = ",".join(email_from_leaf(L) for L in objects)
		url = "mailto:" + recipients
		utils.show_url(url)

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
		Action.__init__(self, _('Send in Email To...'))

	def activate(self, obj, iobj):
		self.activate_multiple((obj, ), (iobj, ))

	def activate_multiple(self, objects, iobjects):
		# FIXME: revisit for unicode email addresses
		recipients = ",".join(email_from_leaf(I) for I in iobjects)
		attachlist = "?attach=" + "&attach=".join(L.object for L in objects)
		url = "mailto:" + recipients + attachlist
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
