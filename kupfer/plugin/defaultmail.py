__kupfer_name__ = _("Default Email Client")
__kupfer_actions__ = ("NewMailAction",)
__description__ = _("Compose email using the system's default mailto: handler")
__version__ = "2017.1"
__author__ = ""

from kupfer import launch
from kupfer.obj import Action, TextLeaf, UrlLeaf
from kupfer.obj.contacts import ContactLeaf, email_from_leaf


class NewMailAction(Action):
    def __init__(self):
        Action.__init__(self, _("Compose Email To"))

    def activate(self, leaf, iobj=None, ctx=None):
        email = email_from_leaf(leaf)
        launch.show_url(f"mailto:{email}")

    def activate_multiple(self, objects):
        recipients = ",".join(filter(None, map(email_from_leaf, objects)))
        url = "mailto:" + recipients
        launch.show_url(url)

    def item_types(self):
        yield ContactLeaf
        yield TextLeaf
        yield UrlLeaf

    def valid_for_item(self, leaf):
        return bool(email_from_leaf(leaf))

    def get_description(self):
        return __description__

    def get_icon_name(self):
        return "mail-message-new"
