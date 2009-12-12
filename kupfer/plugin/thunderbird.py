# -*- coding: UTF-8 -*-

from __future__ import with_statement

import os
import re

from kupfer.objects import (Leaf, Action, Source, TextLeaf, UrlLeaf, RunnableLeaf, 
		FilesystemWatchMixin, AppLeafContentMixin)
from kupfer import utils

from kupfer.plugin import thunderbird_support as support

__kupfer_name__ = _("Thunderbird")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("NewMailAction", )
__description__ = _("Thunderbird Contacts and Actions")
__version__ = "2009-12-12"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


def _get_email_from_url(url):
	''' convert http://foo@bar.pl -> foo@bar.pl '''
	sep = url.find('://')
	return url[sep+3:] if sep > -1 else url

_CHECK_EMAIL_RE = re.compile(r"^[a-z0-9\._%-+]+\@[a-z0-9._%-]+\.[a-z]{2,6}$")

def _check_email(email):
	''' simple email check '''
	return len(email) > 7 and _CHECK_EMAIL_RE.match(email.lower()) is not None


class Contact(Leaf):
	''' Leaf represent single contact from Claws address book '''
	def get_actions(self):
		yield NewMailAction()

	def get_description(self):
		return self.object

	def get_icon_name(self):
		return "stock_person"


class ComposeMail(RunnableLeaf):
	''' Create new mail without recipient '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Compose New Mail"))

	def run(self):
		utils.launch_commandline('thunderbird --compose')

	def get_description(self):
		return _("Compose New Mail with Thunderbird")

	def get_icon_name(self):
		return "mail-message-new"


class NewMailAction(Action):
	''' Createn new mail to selected leaf (Contact or TextLeaf)'''
	def __init__(self):
		Action.__init__(self, _('Compose New Mail To'))

	def activate(self, leaf):
		email = leaf.object
		if isinstance(leaf, UrlLeaf):
			email = _get_email_from_url(email)

		utils.launch_commandline("thunderbird --compose '%s'" % email)

	def get_icon_name(self):
		return "mail-message-new"

	def item_types(self):
		yield Contact
		# we can enter email
		yield TextLeaf
		yield UrlLeaf

	def valid_for_item(self, item):
		if isinstance(item, Contact):
			return True

		elif isinstance(item, TextLeaf):
			return _check_email(item.object)

		elif isinstance(item, UrlLeaf):
			url = _get_email_from_url(item.object)
			return _check_email(url)

		return False


#AppLeafContentMixin
class ContactsSource(Source, FilesystemWatchMixin):
#	appleaf_content_id = 'thunderbird'

	def __init__(self, name=_("Thundrbird Address Book")):
		Source.__init__(self, name)
		self._addrbook_file = support.get_thunderbird_addressbook_file()
		self.unpickle_finish()

	def unpickle_finish(self):
		if not os.path.isdir(self._addrbook_file):
			return

	def get_items(self):
		for name, email in support.get_contacts():
			yield Contact(email, name)

		yield ComposeMail()

	def get_description(self):
		return _("Contacts from Thunderbird Address Book")

	def get_icon_name(self):
		return "thunderbird"

	def provides(self):
		yield Contact
		yield RunnableLeaf



