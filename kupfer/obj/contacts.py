# -*- encoding: utf-8 -*-
"""
Kupfer's Contacts API

Main definition and *constructor* classes.

Constructor classes such as EmailContact are used to conveniently construct
contacts with common traits. To *use* contacts, always use ContactLeaf, asking
for specific slots to be filled.
"""
import re

from kupfer import icons
from kupfer.obj.grouping import GroupingLeaf
from kupfer.plugin.show_text import LargeType

__author__ = ("Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
              "Karol Będkowski <karol.bedkowsk+gh@gmail.com>" )

EMAIL_KEY = "EMAIL"
NAME_KEY = "NAME"
PHONE_KEY = "PHONE"
ADDRESS_KEY = "ADDRESS"
IM_ID_KEY = "IM_ID"
LABEL_KEY = "LABEL"
JABBER_JID_KEY = "JID"
JABBER_STATUS_KEY = "JABBER_STATUS"
JABBER_RESOURCE_KEY = "JABBER_RESOURCE"

class ContactLeaf(GroupingLeaf):
	grouping_slots = (NAME_KEY, )
	def get_icon_name(self):
		return "stock_person"


## E-mail convenience and constructors

def _get_email_from_url(url):
	''' convert http://foo@bar.pl -> foo@bar.pl '''
	sep = url.find('://')
	return url[sep+3:] if sep > -1 else url

# FIXME: Find a more robust (less strict?) approach than regex
_CHECK_EMAIL_RE = re.compile(r"^[a-z0-9\._%-+]+\@[a-z0-9._%-]+\.[a-z]{2,}$")

def is_valid_email(email):
	''' simple email check '''
	return len(email) > 7 and _CHECK_EMAIL_RE.match(email.lower()) is not None

def email_from_leaf(leaf):
	"""
	Return an email address string if @leaf has a valid email address.

	@leaf may also be a TextLeaf or UrlLeaf.
	Return a false value if no valid email is found.
	"""
	if isinstance(leaf, ContactLeaf):
		return EMAIL_KEY in leaf and leaf[EMAIL_KEY]
	email = _get_email_from_url(leaf.object)
	return is_valid_email(email) and email


class EmailContact (ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (EMAIL_KEY, )
	def __init__(self, email, name):
		slots = {EMAIL_KEY: email, NAME_KEY: name}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[EMAIL_KEY]

	def get_description(self):
		return self.object[EMAIL_KEY]

	def get_text_representation(self):
		return self.object[EMAIL_KEY]

	def get_gicon(self):
		return icons.ComposedIconSmall(self.get_icon_name(),"stock_mail")


class JabberContact (ContactLeaf):
	''' Minimal class for all Jabber contacts. '''
	grouping_slots = ContactLeaf.grouping_slots + (JABBER_JID_KEY, )

	def __init__(self, jid, name, status, resource, slots=None):
		jslots = {JABBER_JID_KEY: jid, NAME_KEY: name or jid}
		if slots:
			jslots.update(slots)
		ContactLeaf.__init__(self, jslots, name or jid)

		self._description = _("[%(status)s] %(userid)s/%(service)s") % \
				{
					"status": status,
					"userid": jid,
					"service": resource or u"",
				}

	def repr_key(self):
		return self.object[JABBER_JID_KEY]

	def get_description(self):
		return self._description

class PhoneContact(ContactLeaf):
	def __init__(self, number, name, label):
		slots = {PHONE_KEY: number, NAME_KEY: name, LABEL_KEY: label}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[PHONE_KEY]

	def get_description(self):
		return '%s: %s' %(self.object[LABEL_KEY], self.object[PHONE_KEY])

	def get_actions(self):
		"""returns the action allowed in the leaf"""
		yield LargeType()


class AddressContact(ContactLeaf):
	def __init__(self, address, name, label):
		slots = {ADDRESS_KEY: address, NAME_KEY: name, LABEL_KEY: label}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[ADDRESS_KEY]

	def get_description(self):
		return '%s:\n%s' %(self.object[LABEL_KEY], self.object[ADDRESS_KEY])

	def get_actions(self):
		"""returns the action allowed in the leaf"""
		yield LargeType()


class IMContact(ContactLeaf):
	def __init__(self, im_id, name, label):
		slots = {IM_ID_KEY: im_id, NAME_KEY: name, LABEL_KEY: label}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[IM_ID_KEY]

	def get_description(self):
		return '%s: %s' %(self.object[LABEL_KEY], self.object[IM_ID_KEY])

	def get_actions(self):
		"""returns the action allowed in the leaf"""
		yield LargeType()
