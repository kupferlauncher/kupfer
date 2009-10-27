'''Inspiration from the deskbar pidgin plugin and from the gajim kupfer
plugin'''
import dbus

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer import pretty, icons

__kupfer_name__ = _("Pidgin")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_contents__ = ("ContactsSource", )
__description__ = _("Access to Pidgin Contacts")
__version__ = "0.1"
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
# pylint: disable-msg=W0312


def _create_dbus_connection(activate=False):
	''' Create dbus connection to Pidgin
	@activate: true=starts pidgin if not running
	'''
	interface = None
	obj = None
	sbus = dbus.SessionBus()

	service_name = "im.pidgin.purple.PurpleService"
	obj_name = "/im/pidgin/purple/PurpleObject"
	iface_name = "im.pidgin.purple.PurpleInterface"

	try:
		#check for running pidgin (code from note.py)
		proxy_obj = sbus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
		if activate or dbus_iface.NameHasOwner(service_name):
			obj = sbus.get_object(service_name, obj_name)
		if obj:
			interface = dbus.Interface(obj, iface_name)
	except dbus.exceptions.DBusException, err:
		pretty.print_debug(err)
	return interface


class OpenChat(Action):
	""" Open Chat Conversation Window with jid """

	def __init__(self):
		Action.__init__(self, _('Open Chat'))

	def activate(self, leaf):
		interface = _create_dbus_connection()
		conversation = interface.PurpleConversationNew(1, leaf.account, leaf.jid)
		im = interface.PurpleConvIm(conversation)
		interface.PurpleConvImSend(im, dbus.String(''))

	def get_icon_name(self):
		return 'stock_person'


class PidginContact(Leaf):
	""" Leaf represent single contact from Pidgin """

	def __init__(self, jid, name, account, icon):
		Leaf.__init__(self, name or jid, name or jid)
		if name:
			self._description = "%s <%s>" % (name, jid)
		else:
			self._description = name
		self.account = account
		self.name = name
		self.jid = jid
		self.icon = icon

	def get_actions(self):
		yield OpenChat()

	def get_description(self):
		return self._description

	def get_thumbnail(self, width, height):
		if not self.icon:
			return
		return icons.get_pixbuf_from_file(self.icon, width, height)

	def get_icon_name(self):
		return "pidgin"


class ContactsSource(AppLeafContentMixin, Source):
	''' Get contacts from all on-line accounts in Pidgin via DBus '''
	appleaf_content_id = 'pidgin'

	def __init__(self):
		Source.__init__(self, _('Pidgin Contacts'))

	def _get_buddy_icon(self, interface, buddy):
		''' Lookup the buddy Icon via DBUS Pidgin API '''
		icon = interface.PurpleBuddyGetIcon(buddy)
		if icon != 0:
			return interface.PurpleBuddyIconGetFullPath(icon)

	def get_items(self):
		interface = _create_dbus_connection()
		if interface is None:
			return
		accounts = interface.PurpleAccountsGetAllActive()
		for account in accounts:
			buddies = interface.PurpleFindBuddies(account, dbus.String(''))

			for buddy in buddies:
				if not interface.PurpleBuddyIsOnline(buddy):
					continue

				jid = interface.PurpleBuddyGetName(buddy)
				name = interface.PurpleBuddyGetAlias(buddy)
				icon = self._get_buddy_icon(interface, buddy)
				yield PidginContact(jid, name, account, icon)

	def is_dynamic(self):
		return True

	def get_icon_name(self):
		return 'pidgin'

	def provides(self):
		yield PidginContact


# Local Variables: ***
# python-indent: 8 ***
# indent-tabs-mode: t ***
# End: ***
