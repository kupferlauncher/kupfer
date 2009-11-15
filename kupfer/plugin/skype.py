# -*- coding: UTF-8 -*-

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin, AppLeaf
from kupfer.helplib import PicklingHelperMixin
from kupfer import pretty

__kupfer_name__ = _("Skype")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("ChangeStatus", )
__description__ = _("Access to Skype")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import dbus


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


def _get_skype_connection():
	""" Get dbus Skype object"""
	sbus = dbus.SessionBus(private=True)#, mainloop=mainloop)	
	return _check_skype(sbus)

def _check_skype(bus):
	''' check if Skype is running and login to it '''
	try:
		proxy_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
		if dbus_iface.NameHasOwner(SKYPE_IFACE):
			skype = bus.get_object(SKYPE_IFACE, '/com/Skype')
			if skype:
				if skype.Invoke("NAME Kupfer") != 'OK':
					return None
				if skype.Invoke("PROTOCOL 5") != 'PROTOCOL 5':
					return None
				return skype
	except dbus.exceptions.DBusException, err:
		pretty.print_debug(__name__, '_check_skype', err)
	return None

def _parse_response(response, prefix):
	if response.startswith(prefix):
		return response[len(prefix):].strip()
	return None

def _skype_get_friends():
	skype = _get_skype_connection()
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
		status = skype.Invoke('GET USER %s ONLINESTATUS' % user)
		status = _parse_response(status, 'USER %s ONLINESTATUS' % user)
		yield (user, fullname, status)

def _skype_open_chat(handle):
	skype = _get_skype_connection()
	if not skype:
		return
	resp = skype.Invoke("CHAT CREATE %s" % handle)
	if resp.startswith('CHAT '):
		_chat, chat_id, _status, status = resp.split()
		skype.Invoke('OPEN CHAT %s' % chat_id)

def _skype_call(handle):
	skype = _get_skype_connection()
	if skype:
		skype.Invoke("CALL %s" % handle)

def _skype_set_status(status):
	skype = _get_skype_connection()
	if skype:
		skype.Invoke("SET USERSTATUS %s" % status)


class _SkypeNotify(dbus.service.Object):
	def __init__(self, bus, callback): 
		dbus.service.Object.__init__(self, bus, SKYPE_PATH_CLIENT)
		self._callback = callback

	@dbus.service.method(SKYPE_CLIENT_API, in_signature='s')
	def Notify(self, com):
		pretty.print_debug(__name__, '_SkypeNotify', 'Notify', com)
		self._callback(com)


class _Skype(object):
	""" Handling events from skype"""
	def __init__(self):
		self._callback = None
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

	def bind(self, callback):
		self._callback = callback

	def _signal_dbus_name_owner_changed(self, *args, **kwarg):
		pretty.print_debug(__name__, '_Skype', '_signal_update', args, kwarg)
		skype = _check_skype(self.bus) # and send name and protocol for register Notify
		self._signal_update(*args, **kwarg)

	def _signal_update(self, *args, **kwargs):
		pretty.print_debug(__name__, '_Skype', '_signal_update', args, kwargs)
		if self._callback:
			try:
				self._callback(*args, **kwargs)
			except Exception, err:
				pretty.print_error(__name__, '_Skype', '_signal_update:call', err)

_SKYPE = _Skype()


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
		_skype_open_chat(leaf.object)

	def get_icon_name(self):
		return 'internet-group-chat'


class Call(Action):
	def __init__(self):
		Action.__init__(self, _("Place a Call to Contact"))

	def activate(self, leaf):
		_skype_call(leaf.object)

	def get_icon_name(self):
		return 'call-start'


class ChangeStatus(Action):
	''' Change global status '''
	rank_adjust = 5

	def __init__(self):
		Action.__init__(self, _('Change Global Status To...'))

	def activate(self, leaf, iobj):
		_skype_set_status(iobj.object)

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


class ContactsSource(AppLeafContentMixin, Source, PicklingHelperMixin):
	appleaf_content_id = 'skype'

	def __init__(self):
		Source.__init__(self, _('Skype Contacts'))
		self.unpickle_finish()

	def pickle_prepare(self):
		self.cached_items = None

	def unpickle_finish(self):
		_SKYPE.bind(self._signal_update)
		self.mark_for_update()

	def _signal_update(self, *args, **kwarg):
		pretty.print_debug(__name__, 'ContactsSource', '_signal_update', args,
				kwarg)
		self.mark_for_update()

	def get_items(self):
		#pretty.print_debug(__name__, 'ContactsSource', 'get_items')
		for handle, fullname, status in _skype_get_friends():
			yield Contact((fullname or handle), handle, status)

	def get_icon_name(self):
		return 'skype'

	def provides(self):
		yield Contact


class StatusSource(Source):
	def __init__(self):
		Source.__init__(self, _("Skype Statuses"))

	def get_items(self):
		for status, name in _STATUSES.iteritems():
			yield AccountStatus(status, name)

	def provides(self):
		yield AccountStatus

