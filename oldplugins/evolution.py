# -*- coding: UTF-8 -*-


__kupfer_name__ = _("Evolution")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("NewMailAction", "SendFileByMail")
__description__ = _("Evolution contacts")
__version__ = "2010-02-14"
__author__ = "Francesco Marella, Karol Będkowski"

import evolution

from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf, RunnableLeaf, FileLeaf
from kupfer import utils
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, EmailContact, email_from_leaf


class ComposeMail(RunnableLeaf):
    ''' Create new mail without recipient '''
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Compose New Email"))

    def run(self):
        utils.spawn_async_notify_as("evolution.desktop",
                                   ['evolution', 'mailto:'])

    def get_description(self):
        return _("Compose a new message in Evolution")

    def get_icon_name(self):
        return "mail-message-new"


class NewMailAction(Action):
    ''' Create new mail to selected leaf'''
    def __init__(self):
        Action.__init__(self, _('Compose Email'))

    def activate(self, leaf):
        self.activate_multiple((leaf, ))

    def activate_multiple(self, objects):
        recipients = ",".join(email_from_leaf(L) for L in objects)
        utils.spawn_async(["evolution", "mailto:%s" % recipients])

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield ContactLeaf
        # we can enter email
        yield TextLeaf
        yield UrlLeaf

    def valid_for_item(self, item):
        return bool(email_from_leaf(item))


class SendFileByMail (Action):
    '''Create new e-mail and attach selected file'''
    def __init__(self):
        Action.__init__(self, _('Send in Email To...'))

    def activate(self, obj, iobj):
        self.activate_multiple((obj, ), (iobj, ))

    def activate_multiple(self, objects, iobjects):
        recipients = ",".join(email_from_leaf(I) for I in iobjects)
        attachlist = ["attach=%s" % L.object for L in objects]
        utils.spawn_async(["evolution",
            "mailto:%s?%s" % (recipients, "&".join(attachlist))])

    def item_types(self):
        yield FileLeaf
    def valid_for_item(self, item):
        return not item.is_dir()

    def requires_object(self):
        return True
    def object_types(self):
        yield ContactLeaf
        # we can enter email
        yield TextLeaf
        yield UrlLeaf
    def valid_object(self, iobj, for_item=None):
        return bool(email_from_leaf(iobj))

    def get_description(self):
        return _("Compose new message in Evolution and attach file")
    def get_icon_name(self):
        return "document-send"


class ContactsSource(AppLeafContentMixin, ToplevelGroupingSource):
    appleaf_content_id = 'evolution'

    def __init__(self, name=_("Evolution Address Book")):
        super(ContactsSource, self).__init__(name, "Contacts")

    def get_items(self):
        ebook_ = evolution.ebook.open_addressbook("default")
        if not ebook_:
            return
        for contact in ebook_.get_all_contacts():
            name = contact.get_property("full-name")
            email = contact.get_property("email-1")
            if email:
                yield EmailContact(email, name)

        yield ComposeMail()

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return _("Evolution contacts")

    def get_icon_name(self):
        return "evolution"

    def provides(self):
        yield RunnableLeaf
        yield ContactLeaf

