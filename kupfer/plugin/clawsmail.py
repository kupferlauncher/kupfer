# -*- coding: utf8 -*-
import os
import re
import urllib
from xml.dom import minidom

from kupfer.objects import Leaf, Action, Source, TextLeaf, UrlLeaf, RunnableLeaf
from kupfer.utils import spawn_async

__kupfer_name__ = _("ClawsMail contacts actions")
__kupfer_sources__ = ("ClawsContactsSource", )
__description__ = _("Contacts from ClawsMail")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



class ClawsContactLeaf(Leaf):
	''' Leaf represent single contact from Claws address book '''
	def get_actions(self):
		yield NewMailAction()

	def get_description(self):
		return self.object

	def get_icon_name(self):
		return "stock_person"


class ComposeMailAction(RunnableLeaf):
	''' Create new mail without recipient '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Compose new mail"))

	def run(self):
		spawn_async(('claws-mail', '--compose'))

	def get_description(self):
		return _("Compose new mail with ClawsMail")

	def get_icon_name(self):
		return "stock_mail-compose"


class ReceiveMailAction(RunnableLeaf):
	''' Receive all new mail from all accounts '''
	def __init__(self):
		RunnableLeaf.__init__(self, name=_("Receive all mails"))

	def run(self):
		spawn_async(('claws-mail', '--receive-all'))

	def get_description(self):
		return _("Receive new mail from all accounts by ClawsMail")

	def get_icon_name(self):
		return "stock_mail-receive"


class NewMailAction(Action):
	''' Createn new mail to selected leaf (ClawsContactLeaf or TextLeaf)'''
	def __init__(self):
		Action.__init__(self, _('Write new mail'))

	def activate(self, leaf):
		email = leaf.object
		if isinstance(leaf, UrlLeaf):
			email = NewMailAction._get_email_from_url(email)

		spawn_async(("claws-mail", "--compose", str(email)))

	def get_icon_name(self):
		return 'stock_mail-compose'

	def item_types(self):
		yield ClawsContactLeaf
		# we can enter email
		yield TextLeaf
		yield UrlLeaf

	def valid_for_item(self, item):
		if isinstance(item, ClawsContactLeaf):
			return True

		if isinstance(item, TextLeaf):
			return ClawsContactLeaf._check_email(self.object)

		elif isinstance(item, UrlLeaf):
			url = NewMailAction._get_email_from_url(item.object)
			return ClawsContactLeaf._check_email(url)

		return False

	@staticmethod
	def _get_email_from_url(url):
		sep = url.find('://')
		return url[sep+3:] if sep > -1 else url

	@staticmethod
	def _check_email(email):
		return len(email) > 7 and re.match(r"^[a-z0-9\._%-+]+\@[a-z0-9._%-]+\.[a-z]{2,6}$", email.lower()) is not None



class ClawsContactsSource(Source):
	def __init__(self, name=_("Claws contacts")):
		Source.__init__(self, name)
		self._claws_addrbook_dir = os.path.expanduser('~/.claws-mail/addrbook')
		self._claws_addrbook_index = os.path.join(self._claws_addrbook_dir, "addrbook--index.xml")

	def is_dynamic(self):
		return False

	def get_items(self):
		if os.path.exists(self._claws_addrbook_index):
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
							yield ClawsContactLeaf(email, cn)

				except Exception, err:
					print err

		yield ComposeMailAction()
		yield ReceiveMailAction()

	def get_description(self):
		return _("Session saved in Putty")

	def get_icon_name(self):
		return "claws-mail"

	def provides(self):
		yield ClawsContactLeaf
		yield RunnableLeaf

	def _load_address_books(self):
		''' load list of address-book files '''
		try:
			dtree = minidom.parse(self._claws_addrbook_index)
			for book in dtree.getElementsByTagName('book'):
				yield book.getAttribute('file')

		except Exception, err:
			print err



