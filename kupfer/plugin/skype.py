# -*- coding: UTF-8 -*-
import dbus

from kupfer.objects import Leaf, Action, Source
from kupfer.objects import AppLeafContentMixin, AppLeaf
from kupfer import pretty
from kupfer import plugin_support


__kupfer_name__ = _("Skype")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("ChangeStatus", )
__description__ = _("Access to Skype")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

# This plugin Requires D-Bus to work
plugin_support.check_dbus_connection()

SKYPE_IFACE = 'com.Skype.API'
SKYPE_PATH_CLIENT = '/com/Skype/Client'
SKYPE_CLIENT_API = 'com.Skype.API.Client'

_STATUSES = {
		'ONLINE':	_('Available'),
		'SKYPEME':	_('Skype Me'),
		'AWAY':		_('Away'),
		'NA':		_('Not Available'),
		'DND':		_('Busy'),
		'INVISIBLE':_('Invisible'),
		'OFFLINE':	_('Offline'),
		'LOGGEDOUT': _('Logged Out')
}


def _parse_response(response, prefix):
	if response.startswith(prefix):
		return response[len(prefix):].strip()
	return None


class _SkypeNotify(dbus.service.Object):
	def __init__(self, bus, callback): 
		dbus.service.Object.__init__(self, bus, SKYPE_PATH_CLIENT)
		self._callback = callback

	@dbus.service.method(SKYPE_CLIENT_API, in_signature='s')
	def Notify(self, com):
		pretty.print_debug(__name__, '_SkypeNotify', 'Notify', com)
		self._callback(com)


class Skype(object):
	""" Handling events from skype"""
	__instance__ = None

	@classmethod
	def get(cls):
		if cls.__instance__ is None:
			cls.__instance__ = cls()
		return cls.__instance__

	def __init__(self):
		self._friends = None
		self._authenticated = False
		try:
			self.bus = bus = dbus.Bus()
		except dbus.DBusException, err:
			pretty.print_error(__name__, 'Skype', '__init__', err)
			return
		
		self._dbus_name_owner_watch = bus.add_signal_receiver(
				self._signal_dbus_name_owner_changed,
				'NameOwnerChanged',
				'org.freedesktop.DBus',
				'org.freedesktop.DBus',
				'/org/freedesktop/DBus',
				arg0=SKYPE_IFACE)

		self._skype_notify_callback = _SkypeNotify(bus, self._signal_update)
		self._signal_dbus_name_owner_changed()

	def __del__(self):
		if self.bus:
			self.bus.remove_signal_receiver(self._dbus_name_owner_watch)

		self._dbus_name_owner_watch = None
		self._skype_notify_callback = None


	def _get_skype(self, bus):
		''' Check if Skype is running and login to it.
			Return Skype proxy object.
		'''
		try:
			proxy_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
			dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
			if dbus_iface.NameHasOwner(SKYPE_IFACE):
				skype = bus.get_object(SKYPE_IFACE, '/com/Skype')
				if skype and not self._authenticated:
					resp = skype.Invoke("NAME Kupfer")
					if resp.startswith('ERROR'):
						return None
					resp = skype.Invoke("PROTOCOL 5")
					if  resp != 'PROTOCOL 5':
						return None
					self._authenticated = True
				return skype
		except dbus.exceptions.DBusException, err:
			pretty.print_debug(__name__, 'Skype', '_get_skype', err)
		return None

	def _signal_dbus_name_owner_changed(self, *args, **kwarg):
		pretty.print_debug(__name__, 'Skype', '_signal_dbus_name_owner_changed',
				args, kwarg)
		self._authenticated = False
		self._signal_update(*args, **kwarg)

	def _signal_update(self, *args, **kwargs):
		pretty.print_debug(__name__, 'Skype', '_signal_update', args, kwargs)
		self._friends = None

	def _get_friends(self):
		pretty.print_debug(__name__, 'Skype', '_get_friends')
		self._friends = []
		skype = self._get_skype(self.bus)
		if not skype:
			return
		users =  skype.Invoke("SEARCH FRIENDS")
		if not users.startswith('USERS '):
			return 
		users = users[6:].split(',')
		for user in users:
			user = user.strip()
			fullname = skype.Invoke('GET USER %s FULLNAME' % user)
			fullname = _parse_response(fullname, 'USER %s FULLNAME' % user)
			displayname = skype.Invoke('GET USER %s DISPLAYNAME' % user)
			displayname = _parse_response(displayname, 'USER %s DISPLAYNAME' % user)
			status = skype.Invoke('GET USER %s ONLINESTATUS' % user)
			status = _parse_response(status, 'USER %s ONLINESTATUS' % user)
			contact = Contact((displayname or fullname or user), user, status)
			self._friends.append(contact)

	@property
	def friends(self):
		if self._friends is None:
			self._get_friends()
		return self._friends

	def open_chat(self, handle):
		skype = self._get_skype(self.bus)
		if not skype:
			return
		resp = skype.Invoke("CHAT CREATE %s" % handle)
		if resp.startswith('CHAT '):
			_chat, chat_id, _status, status = resp.split()
			skype.Invoke('OPEN CHAT %s' % chat_id)

	def call(self, handle):
		skype = self._get_skype(self.bus)
		if skype:
			skype.Invoke("CALL %s" % handle)

	def set_status(self, status):
		skype = self._get_skype(self.bus)
		if skype:
			skype.Invoke("SET USERSTATUS %s" % status)


class Contact(Leaf):
	def __init__(self, name, handle, status):
		# @obj should be unique for each contact
		# we use @jid as an alias for this contact
		Leaf.__init__(self, handle, name or handle)

		if name != handle:
			self.name_aliases.add(handle)

		self._description = _("[%(status)s] %(userid)s") % \
			dict(status=status, userid=handle)

	def get_actions(self):
		yield Call()
		yield Chat()

	def get_description(self):
		return self._description

	def get_icon_name(self):
		return "stock_person"


class AccountStatus(Leaf):
	pass


class Chat(Action):
	def __init__(self):
		Action.__init__(self, _("Open Chat Window"))

	def activate(self, leaf):
		Skype.get().open_chat(leaf.object)

	def get_icon_name(self):
		return 'internet-group-chat'


class Call(Action):
	def __init__(self):
		Action.__init__(self, _("Place a Call to Contact"))

	def activate(self, leaf):
		Skype.get().call(leaf.object)

	def get_icon_name(self):
		return 'call-start'


class ChangeStatus(Action):
	''' Change global status '''
	rank_adjust = 5

	def __init__(self):
		Action.__init__(self, _('Change Global Status To...'))

	def activate(self, leaf, iobj):
		Skype.get().set_status(iobj.object)

	def item_types(self):
		yield AppLeaf

	def valid_for_item(self, leaf):
		return leaf.get_id() == 'skype'

	def requires_object(self):
		return True

	def object_types(self):
		yield AccountStatus

	def object_source(self, for_item=None):
		return StatusSource()


class ContactsSource(AppLeafContentMixin, Source):
	appleaf_content_id = 'skype'

	def __init__(self):
		Source.__init__(self, _('Skype Contacts'))


	def get_items(self):
		pretty.print_debug(__name__, 'ContactsSource', 'get_items')
		return Skype.get().friends

	def get_icon_name(self):
		return 'skype'

	def provides(self):
		yield Contact

	def is_dynamic(self):
		return True


class StatusSource(Source):
	def __init__(self):
		Source.__init__(self, _("Skype Statuses"))

	def get_items(self):
		for status, name in _STATUSES.iteritems():
			yield AccountStatus(status, name)

	def provides(self):
		yield AccountStatus

