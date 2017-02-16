__kupfer_name__ = _("Default Email Client")
__kupfer_actions__ = (
    "NewMailAction",
)
__description__ = _("Compose email using the system's default mailto: handler")
__version__ = "2017.1"
__author__ = ""

from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf
from kupfer.obj.contacts import ContactLeaf, email_from_leaf
from kupfer import utils


class NewMailAction(Action):
    def __init__(self):
        Action.__init__(self, _('Compose Email To'))

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
