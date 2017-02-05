# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Gajim")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("ChangeStatus", 'OpenChat')
__description__ = _("Access to Gajim Contacts")
__version__ = "2011-05-12"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import dbus

from kupfer import icons
from kupfer import plugin_support
from kupfer import pretty
from kupfer.objects import Leaf, Action, Source, AppLeaf
from kupfer.weaklib import dbus_signal_connect_weakly
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.contacts import ContactLeaf, JabberContact, JABBER_JID_KEY 
        


plugin_support.check_dbus_connection()

_STATUSES = {
        'online':   _('Available'),
        'chat':     _('Free for Chat'),
        'away':     _('Away'),
        'xa':       _('Not Available'),
        'dnd':      _('Busy'),
        'invisible':_('Invisible'),
        'offline':  _('Offline')
}

_SERVICE_NAME = 'org.gajim.dbus'
_OBJECT_NAME = '/org/gajim/dbus/RemoteObject'
_IFACE_NAME = 'org.gajim.dbus.RemoteInterface'

GAJIM_ACCOUNT_KEY = "GAJIM_ACCOUNT"

def _create_dbus_connection(activate=False):
    ''' Create dbus connection to Gajim 
        @activate: true=starts gajim if not running
    '''
    interface = None
    sbus = dbus.SessionBus()
    try:
        #check for running gajim (code from note.py)
        proxy_obj = sbus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        if activate or dbus_iface.NameHasOwner('org.gajim.dbus'):
            obj = sbus.get_object('org.gajim.dbus', '/org/gajim/dbus/RemoteObject')
            if obj:
                interface = dbus.Interface(obj, 'org.gajim.dbus.RemoteInterface')

    except dbus.exceptions.DBusException as err:
        pretty.print_debug(err)

    return interface


def _check_gajim_version(conn):
    ''' get gajim version. return list lika [0.12.5] '''
    prefs = conn.prefs_list()
    version = prefs['version']
    tversion = list(map(int, version.split('.')))
    if len(tversion) == 2:
        tversion += [0]
    elif len(tversion) > 3:
        # i.e. daily builds
        tversion = tversion[:3]
    return tversion


class GajimContact(JabberContact):
    def __init__(self, jid, name, status, resources, account):
        gajim_slots = { GAJIM_ACCOUNT_KEY: account }
        JabberContact.__init__(self, jid, name, status, resources, gajim_slots)

    def repr_key(self):
        return "".join((self.object[JABBER_JID_KEY], self.object[GAJIM_ACCOUNT_KEY]))

    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "gajim")


class AccountStatus(Leaf):
    pass


class OpenChat(Action):
    def __init__(self):
        Action.__init__(self, _('Open Chat'))

    def activate(self, leaf):
        interface = _create_dbus_connection()
        jid = JABBER_JID_KEY in leaf and leaf[JABBER_JID_KEY]
        account = leaf[GAJIM_ACCOUNT_KEY]
        if interface is not None:
            vmaj,vmin,vbuild = _check_gajim_version(interface)
            if vmaj == 0 and vmin < 13:
                interface.open_chat(jid, account)
            else:
                interface.open_chat(jid, account, '')

    def get_icon_name(self):
        return 'gajim'

    def item_types(self):
        yield ContactLeaf

    def valid_for_item(self, item):
        return GAJIM_ACCOUNT_KEY in item and item[GAJIM_ACCOUNT_KEY]


class ChangeStatus(Action):
    ''' Change global status '''
    rank_adjust = 5

    def __init__(self):
        Action.__init__(self, _('Change Global Status To...'))

    def activate(self, leaf, iobj):
        interface = _create_dbus_connection((iobj.object != 'offline'))
        if interface:
            interface.change_status(iobj.object, '', '')

    def item_types(self):
        yield AppLeaf

    def valid_for_item(self, leaf):
        return leaf.get_id() == 'gajim'

    def requires_object(self):
        return True

    def object_types(self):
        yield AccountStatus

    def object_source(self, for_item=None):
        return StatusSource()


class ContactsSource(AppLeafContentMixin, ToplevelGroupingSource,
        PicklingHelperMixin):
    ''' Get contacts from all on-line accounts in Gajim via DBus '''
    appleaf_content_id = 'gajim'

    def __init__(self, name=_('Gajim Contacts')):
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
        # listen to d-bus signals for updates
        signals = [
            "ContactAbsence",
            "ContactPresence",
            "ContactStatus",
            "AccountPresence",
            "Roster",
            "RosterInfo",
        ]

        session_bus = dbus.Bus()

        for signal in signals:
            dbus_signal_connect_weakly(session_bus, signal,
                    self._signal_update, dbus_interface=_IFACE_NAME)

    def _signal_update(self, *args):
        """catch all notifications to mark for update"""
        self.mark_for_update()

    def get_items(self):
        interface = _create_dbus_connection()
        if interface is not None:
            self._contacts = list(self._find_all_contacts(interface))
        else:
            self._contacts = []
        return self._contacts

    def _find_all_contacts(self, interface):
        for account in interface.list_accounts():
            if interface.get_status(account) == 'offline':
                continue

            for contact in interface.list_contacts(account):
                name = contact['name'] or contact['jid']
                resources = contact['resources'][0][0] if contact['resources'] else ''
                jc = GajimContact(contact['jid'], name, \
                        _STATUSES.get(contact['show'], contact['show']), \
                        resources, account)
                yield jc

    def get_icon_name(self):
        return 'gajim'

    def provides(self):
        yield ContactLeaf


class StatusSource(Source):
    def __init__(self):
        Source.__init__(self, _("Gajim Account Status"))

    def get_items(self):
        for status, name in _STATUSES.items():
            yield AccountStatus(status, name)

    def provides(self):
        yield AccountStatus

