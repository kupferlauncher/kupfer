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


def _get_skype_connection():
	"""docstring for _send_command_to_skype"""
	sbus = dbus.SessionBus(private=True)#, mainloop=mainloop)	
	try:
		#check for running gajim (code from note.py)
		proxy_obj = sbus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
		if dbus_iface.NameHasOwner('com.Skype.API'):
			skype = sbus.get_object('com.Skype.API', '/com/Skype')
			if skype:
				if skype.Invoke("NAME Kupfer") != 'OK':
					return None
				if skype.Invoke("PROTOCOL 5") != 'PROTOCOL 5':
					return None
				return skype

	except dbus.exceptions.DBusException, err:
		pretty.print_debug(err)

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

class _SkypeNotifyCallback(dbus.service.Object):
	def __init__(self, bus, callback):
		dbus.service.Object.__init__(self, bus, '/com/Skype/Client')
		self._callback = callback

	@dbus.service.method(dbus_interface='com.Skype.API.Client')
	def Notify(self, com):
		self._callback(com)


class ContactsSource(AppLeafContentMixin, Source, PicklingHelperMixin):
	''' Get contacts from all on-line accounts in Gajim via DBus '''
	appleaf_content_id = 'skype'

	def __init__(self):
		Source.__init__(self, _('Skype Contacts'))
		self.unpickle_finish()

	def pickle_prepare(self):
		self._skype_notify_callback = None
		self._sbus = None
		self._dbus_loop = None

	def unpickle_finish(self):
		try:
			bus = dbus.Bus()
		except dbus.DBusException, err:
			return
		
		self.dbus_name_owner_watch = bus.add_signal_receiver(self._signal_update,
			'NameOwnerChanged',
			'org.freedesktop.DBus',
			'org.freedesktop.DBus',
			'/org/freedesktop/DBus',
			arg0='com.Skype.API')

		# this don't work 
		from dbus.mainloop.glib import DBusGMainLoop
		self._dbus_loop = DBusGMainLoop()
		self._sbus = sbus = dbus.SessionBus(private=True, mainloop=self._dbus_loop)
		self._skype_notify_callback = _SkypeNotifyCallback(sbus, self._signal_update)


	def _signal_update(self, *arg, **kwarg):
		self.mark_for_update()

	def get_items(self):
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

