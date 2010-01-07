# -*- encoding: utf-8 -*-
"""
Kupfer's Contacts API
"""
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

