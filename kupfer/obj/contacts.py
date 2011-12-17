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

__author__ = ("Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
              "Karol Będkowski <karol.bedkowsk+gh@gmail.com>",
              "Adi Sieker <adi@sieker.info>",
)

EMAIL_KEY = "EMAIL"
NAME_KEY = "NAME"
PHONE_KEY = "PHONE"
ADDRESS_KEY = "ADDRESS"
LABEL_KEY = "LABEL"
JABBER_JID_KEY = "JID"
JABBER_STATUS_KEY = "JABBER_STATUS"
JABBER_RESOURCE_KEY = "JABBER_RESOURCE"
AIM_KEY = "AIM"
GOOGLE_TALK_KEY = "GOOGLE_TALK"
ICQ_KEY = "ICQ"
MSN_KEY = "MSN"
QQ_KEY = "QQ"
SKYPE_KEY = "SKYPE"
YAHOO_KEY = "YAHOO"


class ContactLeaf(GroupingLeaf):
	grouping_slots = (NAME_KEY, )

	def get_icon_name(self):
		return "stock_person"

	def get_text_representation(self):
		return self.get_description()

## E-mail convenience and constructors

def _get_email_from_url(url):
	''' convert http://foo@bar.pl -> foo@bar.pl '''
	sep = url.find('://')
	return url[sep + 3:] if sep > -1 else url

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

	def get_gicon(self):
		return icons.ComposedIconSmall(self.get_icon_name(), "stock_mail")


class IMContact (ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (EMAIL_KEY, )

	def __init__(self, im_id_kind, im_id, name, label=None, other_slots=None):
		self.im_id_kind = im_id_kind
		slots = {im_id_kind: im_id, NAME_KEY: name, LABEL_KEY: label}
		if other_slots:
			slots.update(other_slots)
		ContactLeaf.__init__(self, slots, name)
		self.kupfer_add_alias(im_id)

	def repr_key(self):
		return self.object[self.im_id_kind]

	def get_description(self):
		return self.object[LABEL_KEY] or self.object[self.im_id_kind]


class JabberContact (IMContact):
	''' Minimal class for all Jabber contacts. '''
	grouping_slots = IMContact.grouping_slots + (JABBER_JID_KEY, )

	def __init__(self, jid, name, status=None, resource=None, slots=None):
		IMContact.__init__(self, JABBER_JID_KEY, jid, name or jid,
				other_slots=slots)
		self._description = _("[%(status)s] %(userid)s/%(service)s") % \
				{
					"status": status or _("unknown"),
					"userid": jid,
					"service": resource or u"",
				}

	def get_description(self):
		return self._description


class AIMContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (AIM_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, AIM_KEY, id_, name, _("Aim"), slots)


class GoogleTalkContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (GOOGLE_TALK_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, GOOGLE_TALK_KEY, id_, name, _("Google Talk"),
				slots)


class ICQContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (ICQ_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, ICQ_KEY, id_, name, _("ICQ"), slots)


class MSNContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (MSN_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, MSN_KEY, id_, name, _("MSN"), slots)


class QQContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (QQ_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, QQ_KEY, id_, name, _("QQ"), slots)


class YahooContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (YAHOO_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, YAHOO_KEY, id_, name, _("Yahoo"), slots)


class SkypeContact(IMContact):
	grouping_slots = IMContact.grouping_slots + (SKYPE_KEY, )

	def __init__(self, id_, name, slots=None):
		IMContact.__init__(self, SKYPE_KEY, id_, name, _("Skype"), slots)


class PhoneContact(ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (EMAIL_KEY, )

	def __init__(self, number, name, label, slots=None):
		pslots = {PHONE_KEY: number, NAME_KEY: name, LABEL_KEY: label}
		if slots:
			pslots.update(slots)
		ContactLeaf.__init__(self, pslots, name)

	def repr_key(self):
		return self.object[PHONE_KEY]

	def get_description(self):
		return '%s: %s' % (self.object[LABEL_KEY], self.object[PHONE_KEY])


class AddressContact(ContactLeaf):
	grouping_slots = ContactLeaf.grouping_slots + (EMAIL_KEY, )

	def __init__(self, address, name, label, slots=None):
		aslots = {ADDRESS_KEY: address, NAME_KEY: name, LABEL_KEY: label}
		if slots:
			aslots.update(slots)
		ContactLeaf.__init__(self, aslots, name)

	def repr_key(self):
		return self.object[ADDRESS_KEY]
