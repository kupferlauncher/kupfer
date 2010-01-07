# -*- encoding: utf-8 -*-
"""
Kupfer's Contacts API

Main definition and *constructor* classes.

Constructor classes such as EmailContact are used to conveniently construct
contacts with common traits. To *use* contacts, always use ContactLeaf, asking
for specific slots to be filled.
"""
import re

from kupfer.obj.grouping import GroupingLeaf

__author__ = ("Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
              "Karol Będkowski <karol.bedkowsk+gh@gmail.com>" )

EMAIL_KEY = "EMAIL"
NAME_KEY = "NAME"
JID_KEY = "JID"

CONTACTS_CATEGORY = "Contacts"

class ContactLeaf(GroupingLeaf):
	grouping_slots = (EMAIL_KEY, NAME_KEY)
	def get_icon_name(self):
		return "stock_person"


## E-mail convenience and constructors

def _get_email_from_url(url):
	''' convert http://foo@bar.pl -> foo@bar.pl '''
	sep = url.find('://')
	return url[sep+3:] if sep > -1 else url

_CHECK_EMAIL_RE = re.compile(r"^[a-z0-9\._%-+]+\@[a-z0-9._%-]+\.[a-z]{2,6}$")

def _check_email(email):
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
	return _check_email(email) and email


class EmailContact (ContactLeaf):
	def __init__(self, email, name):
		slots = {EMAIL_KEY: email, NAME_KEY: name}
		ContactLeaf.__init__(self, slots, name)

	def repr_key(self):
		return self.object[EMAIL_KEY]

	def get_description(self):
		return self.object[EMAIL_KEY]


class JabberContact (ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (JID_KEY, )
	def __init__(self, jid, name, accout, status, resource):
		slots = {JID_KEY: jid, NAME_KEY: name}
		ContactLeaf.__init__(self, slots, name)
		self.accout = accout
		self.status = status
		self.resource = resource

		self._description = _("[%(status)s] %(userid)s/%(service)s") % \
				{
					"status": status,
					"userid": jid,
					"service": resource[0][0] if resource else u"",
				}

	def repr_key(self):
		return self.object[JID_KEY]

	def get_description(self):
		return self._description

