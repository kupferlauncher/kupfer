# -*- coding: UTF-8 -*-
import os
import re
from xml.dom import minidom

from kupfer.objects import (Leaf, Action, Source, TextLeaf, UrlLeaf, RunnableLeaf, 
		FilesystemWatchMixin, AppLeafContentMixin, FileLeaf)
from kupfer import utils

__kupfer_name__ = _("Claws Mail")
__kupfer_sources__ = ("ClawsContactsSource", )
__kupfer_actions__ = ("NewMailAction", "SendFileByMail")
__description__ = _("Claws Mail Contacts and Actions")
__version__ = "0.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


def _get_email_from_url(url):
	''' convert http://foo@bar.pl -> foo@bar.pl '''
	sep = url.find('://')
	return url[sep+3:] if sep > -1 else url

_CHECK_EMAIL_RE = re.compile(r"^[a-z0-9\._%-+]+\@[a-z0-9._%-]+\.[a-z]{2,6}$")

def _check_email(email):
	''' simple email check '''
	return len(email) > 7 and _CHECK_EMAIL_RE.match(email.lower()) is not None


class ClawsContact(Leaf):
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
		utils.launch_commandline('claws-mail --compose')

	def get_description(self):
		return _("Compose New Mail with Claws Mail")

	def get_icon_name(self):
		return "mail-message-new"


class ReceiveMail(RunnableLeaf):
	''' Receive all new mail from all accounts '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Receive All Mails"))

	def run(self):
		utils.launch_commandline('claws-mail --receive-all')

	def get_description(self):
		return _("Receive new mail from all accounts by ClawsMail")

	def get_icon_name(self):
		return "mail-send-receive"


class NewMailAction(Action):
	''' Createn new mail to selected leaf (ClawsContact or TextLeaf)'''
	def __init__(self):
		Action.__init__(self, _('Compose New Mail To'))

	def activate(self, leaf):
		email = leaf.object
		if isinstance(leaf, UrlLeaf):
			email = _get_email_from_url(email)

		utils.launch_commandline("claws-mail --compose '%s'" % email)

	def get_icon_name(self):
		return "mail-message-new"

	def item_types(self):
		yield ClawsContact
		# we can enter email
		yield TextLeaf
		yield UrlLeaf

	def valid_for_item(self, item):
		if isinstance(item, ClawsContact):
			return True

		elif isinstance(item, TextLeaf):
			return _check_email(item.object)

		elif isinstance(item, UrlLeaf):
			url = _get_email_from_url(item.object)
			return _check_email(url)

		return False


class SendFileByMail(Action):
	''' Createn new mail and attach selected file'''
	def __init__(self):
		Action.__init__(self, _('Send File by Mail'))

	def activate(self, leaf):
		filepath = leaf.object
		utils.launch_commandline("claws-mail --attach '%s'" % filepath)

	def get_icon_name(self):
		return "mail-message-new"

	def item_types(self):
		yield FileLeaf

	def get_description(self):
		return _("Create new mail in ClawsMail and attach selected file")


class ClawsContactsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = 'claws-mail'

	def __init__(self, name=_("Claws Mail Address Book")):
		Source.__init__(self, name)
		self._claws_addrbook_dir = os.path.expanduser('~/.claws-mail/addrbook')
		self._claws_addrbook_index = os.path.join(self._claws_addrbook_dir, \
				"addrbook--index.xml")
		self.unpickle_finish()

	def unpickle_finish(self):
		if not os.path.isdir(self._claws_addrbook_dir):
			return

		self.monitor_token = self.monitor_directories(self._claws_addrbook_dir)

	def monitor_include_file(self, gfile):
		# monitor only addrbook-*.xml files
		return gfile and gfile.get_basename().endswith('.xml') and \
				gfile.get_basename().startswith("addrbook-")

	def get_items(self):
		if os.path.isfile(self._claws_addrbook_index):
			for addrbook_file in self._load_address_books():
				addrbook_filepath = os.path.join(self._claws_addrbook_dir, addrbook_file)
				if not os.path.exists(addrbook_filepath):
					continue

				try:
					dtree = minidom.parse(addrbook_filepath)
					persons = dtree.getElementsByTagName('person')
					for person in persons:
						cn = person.getAttribute('cn')
						addresses = person.getElementsByTagName('address')
						for address in addresses:
							email = address.getAttribute('email')
							yield ClawsContact(email, cn)

				except StandardError, err:
					self.output_error(err)

		yield ComposeMail()
		yield ReceiveMail()

	def get_description(self):
		return _("Contacts from Claws Mail Address Book")

	def get_icon_name(self):
		return "claws-mail"

	def provides(self):
		yield ClawsContact
		yield RunnableLeaf

	def _load_address_books(self):
		''' load list of address-book files '''
		try:
			dtree = minidom.parse(self._claws_addrbook_index)
			for book in dtree.getElementsByTagName('book'):
				yield book.getAttribute('file')

		except StandardError, err:
			self.output_error(err)



