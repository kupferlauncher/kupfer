__kupfer_name__ = _("Kopete")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("ChangeStatus", 'OpenChat')
__description__ = _("Access to Kopete Contacts")
__version__ = "2011-10-15"
__author__ = "Aleksei Gusev <aleksei.gusev@gmail.com>"

import dbus
import time

from kupfer import icons
from kupfer import plugin_support
from kupfer.objects import Leaf, Action, Source, AppLeaf
from kupfer.weaklib import dbus_signal_connect_weakly
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, JabberContact, JABBER_JID_KEY

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "show_offline",
		"label": _("Show offline contacts"),
		"type": bool,
		"value": False,
		},
	)

plugin_support.check_dbus_connection()

_STATUSES = {
	'available':	_('Available'),
	'away':		_('Away'),
	'dnd':		_('Busy'),
	'hidden':	_('Invisible'),
	'offline':	_('Offline')
	}

_ICONS_BY_STATUSES = {
	'Offline': 'user-offline',
	'Away': 'user-away',
	'Online': 'user-available'
	}

ACCOUNTMANAGER_PATH = "/Kopete"
ACCOUNTMANAGER_IFACE = "org.kde.kopete"
DBUS_PROPS_IFACE = "org.kde.Kopete"
KOPETE_CONTACT_ID = "KOPETE_CONTACT_ID"

def _create_dbus_connection():
	sbus = dbus.SessionBus()
	proxy_obj = sbus.get_object(ACCOUNTMANAGER_IFACE, ACCOUNTMANAGER_PATH)
	dbus_iface = dbus.Interface(proxy_obj, DBUS_PROPS_IFACE)
	return dbus_iface

class KopeteContact(JabberContact):
	def __init__(self, jid, name, status, resources, icon_path, contact_id):
		self._kopete_icon_path = icon_path
		kopete_slots = { KOPETE_CONTACT_ID: contact_id }
		JabberContact.__init__(self, jid, name, status, resources, kopete_slots)
		self._description = _("[%(status)s] %(name)s") % { "status": status,  "name": name }
		self._status = status

	def get_thumbnail(self, width, height):
		if self._kopete_icon_path:
			return icons.get_pixbuf_from_file(self._kopete_icon_path, width, height)
		else:
			return None

	def get_icon_name(self):
		return _ICONS_BY_STATUSES[self._status] or 'user-available'

class OpenChat(Action):

	def __init__(self):
		Action.__init__(self, _('Open Chat'))

	def activate(self, leaf):
		contact_id = leaf[KOPETE_CONTACT_ID]
		_create_dbus_connection().openChat(contact_id)

	def item_types(self):
		yield KopeteContact

class AccountStatus(Leaf):
	pass

class ChangeStatus(Action):
	''' Change global status '''

	def __init__(self):
		Action.__init__(self, _('Change Global Status To...'))

	def activate(self, leaf, iobj):
		interface = _create_dbus_connection()
		interface.setOnlineStatus(_STATUSES.get(iobj.object))

	def item_types(self):
		yield AppLeaf

	def valid_for_item(self, leaf):
		print leaf.get_id()
		return leaf.get_id() == 'kopete'

	def requires_object(self):
		return True

	def object_types(self):
		yield AccountStatus

	def object_source(self, for_item=None):
		return StatusSource()

class ContactsSource(AppLeafContentMixin, ToplevelGroupingSource,
		     PicklingHelperMixin):
	''' Get contacts from all on-line accounts in Kopete via DBus '''
	appleaf_content_id = 'kopete'

	def __init__(self, name=_('Kopete Contacts')):
		super(ContactsSource, self).__init__(name, "Contacts")
		self._version = 2
		self.unpickle_finish()

	def pickle_prepare(self):
		self._contacts = []

	def unpickle_finish(self):
		self.mark_for_update()
		self._contacts = []

	def initialize(self):
		ToplevelGroupingSource.initialize(self)

	def get_items(self):
		interface = _create_dbus_connection()
		if interface is not None:
			self._contacts = list(self._find_all_contacts(interface))
		else:
			self._contacts = []
		return self._contacts

	def _find_all_contacts(self, interface):
		show_offline = __kupfer_settings__["show_offline"]
		bus = dbus.SessionBus()
		for contact_id in interface.contacts():
			contact = interface.contactProperties(contact_id)

			show_offline = __kupfer_settings__["show_offline"]
			if not (show_offline or interface.isContactOnline(contact_id)):
				continue
			else:
				yield KopeteContact(contact['display_name'],
						    contact['display_name'],
						    contact['status'],
						    '',
						    contact['picture'],
						    contact_id)

	def get_icon_name(self):
		return 'kopete'

	def provides(self):
		yield KopeteContact

class StatusSource(Source):
	def __init__(self):
		Source.__init__(self, _("Kopete Account Status"))

	def get_items(self):
		for status, name in _STATUSES.iteritems():
			yield AccountStatus(status, name)

	def provides(self):
		yield AccountStatus
