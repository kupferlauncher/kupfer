# -*- coding: UTF-8 -*-

from __future__ import with_statement

import os
import re

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import TextLeaf, UrlLeaf, RunnableLeaf, AppLeafContentMixin
from kupfer.helplib import FilesystemWatchMixin
from kupfer import utils, icons

from kupfer.plugin import thunderbird_support as support

__kupfer_name__ = _("Thunderbird")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("NewMailAction", )
__description__ = _("Thunderbird/Icedove Contacts and Actions")
__version__ = "2009-12-13"
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
	''' Leaf represents a single contact from the address book '''
	def get_description(self):
		return self.object

	def get_icon_name(self):
		return "stock_person"


class ComposeMail(RunnableLeaf):
	''' Create new mail without recipient '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Compose New Mail"))

	def run(self):
		if not utils.launch_commandline('thunderbird --compose'):
			utils.launch_commandline('icedove --compose')

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

		if not utils.launch_commandline("thunderbird mailto:%s" % email):
			utils.launch_commandline("icedove mailto:%s" % email)

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


class ContactsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = ('thunderbird', 'icedove')

	def __init__(self, name=_("Thunderbird Address Book")):
		Source.__init__(self, name)

	def initialize(self):
		abook_dir = support.get_addressbook_dir()
		if not abook_dir or not os.path.isdir(abook_dir):
			return
		self.monitor_token = self.monitor_directories(abook_dir)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() == support.ABOOK_FILE

	def get_items(self):
		for name, email in support.get_contacts():
			yield Contact(email, name)

		yield ComposeMail()

	def get_description(self):
		return _("Contacts from Thunderbird Address Book")

	def get_gicon(self):
		return icons.get_gicon_with_fallbacks(None, ("thunderbird", "icedove"))

	def provides(self):
		yield Contact
		yield RunnableLeaf



