# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Opera Mail")
__kupfer_sources__ = ("OperaContactsSource", )
__kupfer_actions__ = ("NewMailAction", )
__description__ = _("Opera Mail contacts and actions")
__version__ = "2010-10-19"
__author__ = "Chris Parsons <cjparsons1@yahoo.co.uk>"

import codecs
import os

from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf, RunnableLeaf
from kupfer import utils
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, EmailContact, email_from_leaf


CONTACTS_FILE = "contacts.adr"


class ComposeMail(RunnableLeaf):
    ''' Create new mail without recipient '''
    def __init__(self):
        RunnableLeaf.__init__(self, name=_("Compose New Email"))

    def run(self):
        utils.spawn_async(['opera', '-remote', 'openComposer()'])

    def get_description(self):
        return _("Compose a new message in Opera Mail")

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
        utils.spawn_async(['opera', '-remote', 'openURL(mailto:%s)' % recipients])

    def get_icon_name(self):
        return "mail-message-new"

    def item_types(self):
        yield ContactLeaf
        yield TextLeaf
        yield UrlLeaf

    def valid_for_item(self, item):
        return bool(email_from_leaf(item))


class OperaContactsSource(ToplevelGroupingSource, FilesystemWatchMixin):

    def __init__(self, name=_("Opera Mail Contacts")):
        super(OperaContactsSource, self).__init__(name, "Contacts")
        self._opera_home = os.path.expanduser("~/.opera/")
        self._contacts_path = os.path.join(self._opera_home, CONTACTS_FILE)

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        if not os.path.isdir(self._opera_home):
            return

        self.monitor_token = self.monitor_directories(self._opera_home)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == CONTACTS_FILE

    def get_items(self):
        name = None
        folderList = ['TopLevel']
        TRASH = 'XXXTRASHXXX'
        try:
            with codecs.open(self._contacts_path, "r", "UTF-8") as bfile:
                for line in bfile:
                    line = line.strip()
                    if line.startswith('-'):
                        folderList.pop()
                    elif line.startswith('#FOLDER'):
                        entryType = 'Folder'
                    elif line.startswith('#CONTACT'):
                        entryType = 'Contact'
                    elif line.startswith('TRASH FOLDER=YES'):
                        folderList[-1] = TRASH
                    elif line.startswith('NAME='):
                        name = line[5:]
                        if entryType == 'Folder':
                            folderList.append(name)
                    elif line.startswith('MAIL=') and name and \
                            entryType == 'Contact' and not TRASH in folderList:
                        # multiple addresses separated with
                        # two Ctrl-B (\x02) characters
                        emails = line[5:].split('\x02\x02')
                        for e in emails:
                            yield EmailContact(e, name)
        except EnvironmentError as exc:
            self.output_error(exc)
        except UnicodeError as exc:
            self.output_error("File %s not in expected encoding (UTF-8)" %
                    self._bookmarks_path)
            self.output_error(exc)
        yield ComposeMail()

    def should_sort_lexically(self):
        # since it is a grouping source, grouping and non-grouping will be
        # separate and only grouping leaves will be sorted
        return True

    def get_description(self):
        return _("Contacts from Opera Mail")

    def get_icon_name(self):
        return "opera"

    def provides(self):
        yield RunnableLeaf
        yield ContactLeaf
# vi:nosmarttab:noexpandtab:ts=4:sw=4
