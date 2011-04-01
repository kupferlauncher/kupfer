# -*- coding: utf-8 -*-

from __future__ import with_statement
__kupfer_name__ = _("Thunderbird")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("NewMailAction", )
__description__ = _("Thunderbird/Icedove Contacts and Actions")
__version__ = "2009-12-13"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os

from kupfer.objects import Action
from kupfer.objects import TextLeaf, UrlLeaf, RunnableLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer import utils, icons
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, EmailContact, email_from_leaf

from kupfer.plugin import thunderbird_support as support




class ComposeMail(RunnableLeaf):
	''' Create new mail without recipient '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Compose New Email"))

	def run(self):
		if not utils.spawn_async(['thunderbird', '--compose']):
			utils.spawn_async(['icedove', '--compose'])

	def get_description(self):
		return _("Compose a new message in Thunderbird")

	def get_icon_name(self):
		return "mail-message-new"


class NewMailAction(Action):
	''' Createn new mail to selected leaf (Contact or TextLeaf)'''
	def __init__(self):
		Action.__init__(self, _('Compose Email'))

	def activate(self, leaf):
		email = email_from_leaf(leaf)

		if not utils.spawn_async(['thunderbird', 'mailto:%s' % email]):
			utils.spawn_async(['icedove', 'mailto:%s' % email])

	def get_icon_name(self):
		return "mail-message-new"

	def item_types(self):
		yield ContactLeaf
		# we can enter email
		yield TextLeaf
		yield UrlLeaf

	def valid_for_item(self, item):
		return bool(email_from_leaf(item))

class ContactsSource(AppLeafContentMixin, ToplevelGroupingSource,
		FilesystemWatchMixin):
	appleaf_content_id = ('thunderbird', 'icedove')

	def __init__(self, name=_("Thunderbird Address Book")):
		ToplevelGroupingSource.__init__(self, name, "Contacts")
		self._version = 2

	def initialize(self):
		ToplevelGroupingSource.initialize(self)
		abook_dir = support.get_addressbook_dir()
		if not abook_dir or not os.path.isdir(abook_dir):
			return
		self.monitor_token = self.monitor_directories(abook_dir)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename().endswith('.mab')

	def get_items(self):
		for name, email in support.get_contacts():
			yield EmailContact(email, name)

		yield ComposeMail()

	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("Contacts from Thunderbird Address Book")

	def get_gicon(self):
		return icons.get_gicon_with_fallbacks(None, ("thunderbird", "icedove"))

	def provides(self):
		yield ContactLeaf
		yield RunnableLeaf



