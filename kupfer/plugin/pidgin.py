'''Inspiration from the deskbar pidgin plugin and from the gajim kupfer
plugin'''
__kupfer_name__ = _("Pidgin")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = (
    "OpenChat",
    "SendMessage",
)
__description__ = _("Access to Pidgin Contacts")
__author__ = ("Chmouel Boudjnah <chmouel@chmouel.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>")
__version__ = "2017.1"

import dbus

from kupfer.objects import Action, TextLeaf, TextSource
from kupfer import pretty, scheduler
from kupfer import icons
from kupfer import plugin_support
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.weaklib import dbus_signal_connect_weakly
from kupfer.obj.contacts import NAME_KEY, EMAIL_KEY, ContactLeaf, is_valid_email

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "show_offline",
        "label": _("Show offline contacts"),
        "type": bool,
        "value": False,
    },
)

plugin_support.check_dbus_connection()

# Contact data contstants
PIDGIN_ACCOUNT = "_PIDGIN_ACCOUNT"
PIDGIN_JID = "_PIDGIN_JID"

# D-Bus "addresses"
SERVICE_NAME = "im.pidgin.purple.PurpleService"
OBJECT_NAME = "/im/pidgin/purple/PurpleObject"
IFACE_NAME = "im.pidgin.purple.PurpleInterface"

def _create_dbus_connection(activate=False):
    ''' Create dbus connection to Pidgin
    @activate: true=starts pidgin if not running
    '''
    interface = None
    obj = None
    sbus = dbus.SessionBus()

    try:
        #check for running pidgin (code from note.py)
        proxy_obj = sbus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        if activate or dbus_iface.NameHasOwner(SERVICE_NAME):
            obj = sbus.get_object(SERVICE_NAME, OBJECT_NAME)
        if obj:
            interface = dbus.Interface(obj, IFACE_NAME)
    except dbus.exceptions.DBusException as err:
        pretty.print_debug(err)
    return interface


def _send_message_to_contact(pcontact, message, present=False):
    """
    Send @message to PidginContact @pcontact
    """
    interface = _create_dbus_connection()
    if not interface:
        return
    account = pcontact[PIDGIN_ACCOUNT]
    jid = pcontact[PIDGIN_JID]
    conversation = interface.PurpleConversationNew(1, account, jid)
    im = interface.PurpleConvIm(conversation)
    interface.PurpleConvImSend(im, message)
    if present:
        interface.PurpleConversationPresent(conversation)

class ContactAction (Action):
    def get_required_slots(self):
        return ()
    def item_types(self):
        yield ContactLeaf
    def valid_for_item(self, leaf):
        return all(slot in leaf for slot in self.get_required_slots())

class OpenChat(ContactAction):
    """ Open Chat Conversation Window with jid """
    # consider it as main action for pidgin contacts
    rank_adjust = 5

    def __init__(self):
        Action.__init__(self, _('Open Chat'))

    def activate(self, leaf):
        _send_message_to_contact(leaf, "", present=True)

    def get_required_slots(self):
        return [PIDGIN_ACCOUNT, PIDGIN_JID]

class ChatTextSource (TextSource):
    def get_rank(self):
        return 100
    def get_text_items(self, text):
        n = len(text)
        summary = text[:10] + (text[10:11] and "..")
        desc_template = ngettext("%s (%d character)", "%s (%d characters)", n)
        yield TextLeaf(text, desc_template % (summary, n))

    def get_items(self, text):
        return self.get_text_items(text)

class SendMessage (ContactAction):
    """ Send chat message directly from Kupfer """
    def __init__(self):
        Action.__init__(self, _("Send Message..."))

    def activate(self, leaf, iobj):
        _send_message_to_contact(leaf, iobj.object)

    def get_required_slots(self):
        return [PIDGIN_ACCOUNT, PIDGIN_JID]

    def requires_object(self):
        return True
    def object_types(self):
        yield TextLeaf
    def object_source(self, for_item=None):
        return TextSource()
    def valid_object(self, iobj, for_item=None):
        # ugly, but we don't want derived text
        return type(iobj) is TextLeaf

class PidginContact(ContactLeaf):
    """ Leaf represent single contact from Pidgin """
    grouping_slots = ContactLeaf.grouping_slots + (EMAIL_KEY, )
    def __init__(self, jid, name, account, icon, protocol, available,
        status_message):
        slots = {
            EMAIL_KEY: jid,
            NAME_KEY: name or jid,
            PIDGIN_ACCOUNT: account,
            PIDGIN_JID: jid,
        }
        if not is_valid_email(jid):
            slots[EMAIL_KEY] = None

        ContactLeaf.__init__(self, slots, name or jid)

        self.kupfer_add_alias(jid)

        self._description = _("[%(status)s] %(userid)s/%(service)s") % \
                {
                    "status": _("Available") if available else _("Away"),
                    "userid": jid,
                    "service": protocol,
                }

        if status_message:
            self._description += "\n%s" % status_message

        self.account = account
        self.jid = jid
        self.icon = icon
        self.protocol = protocol

    def repr_key(self):
        # the repr key should be persistent and hopefully unique
        return "%s, %s" % (self.protocol, self.object[PIDGIN_JID])

    def get_description(self):
        return self._description

    def get_thumbnail(self, width, height):
        if not self.icon:
            return
        return icons.get_pixbuf_from_file(self.icon, width, height)

    def get_icon_name(self):
        return "stock_person"


class ContactsSource(AppLeafContentMixin, ToplevelGroupingSource):
    ''' Get contacts from all on-line accounts in Pidgin via DBus '''
    appleaf_content_id = 'pidgin'
    source_use_cache = False

    def __init__(self):
        ToplevelGroupingSource.__init__(self, _('Pidgin Contacts'), "Contacts")
        self._version = 5
        self.all_buddies = {}

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        self._install_dbus_signal()
        self._buddy_update_timer = scheduler.Timer()
        self._buddy_update_queue = set()

    def _get_pidgin_contact(self, interface, buddy, account=None, protocol=None):
        if not account:
            account = interface.PurpleBuddyGetAccount(buddy)

        if not protocol:
            protocol = interface.PurpleAccountGetProtocolName(account)

        jid = interface.PurpleBuddyGetName(buddy)
        name = interface.PurpleBuddyGetAlias(buddy)
        _icon = interface.PurpleBuddyGetIcon(buddy)
        icon = None
        if _icon != 0:
            icon = interface.PurpleBuddyIconGetFullPath(_icon)
        presenceid = interface.PurpleBuddyGetPresence(buddy)
        statusid = interface.PurplePresenceGetActiveStatus(presenceid)
        availability = interface.PurplePresenceIsAvailable(presenceid)
        status_message = interface.PurpleStatusGetAttrString(statusid, "message")

        return PidginContact(jid, name, account, icon, protocol, availability,
                status_message)

    def _get_all_buddies(self):
        interface = _create_dbus_connection()
        if interface is None:
            return

        accounts = interface.PurpleAccountsGetAllActive()
        show_offline = __kupfer_settings__["show_offline"]
        for account in accounts:
            buddies = interface.PurpleFindBuddies(account, dbus.String(''))
            protocol = interface.PurpleAccountGetProtocolName(account)

            for buddy in buddies:
                if not (show_offline or interface.PurpleBuddyIsOnline(buddy)):
                    continue

                self.all_buddies[buddy] = self._get_pidgin_contact(interface,
                        buddy, protocol=protocol, account=account)

    def _remove_buddies_not_connected(self):
        """ Remove buddies that belong to accounts no longer connected """
        if not self.all_buddies:
            return
        interface = _create_dbus_connection()
        if interface is None:
            self.all_buddies = {}
            return

        try:
            # extra careful as this will fail when Pidgin is Quitting
            accounts = interface.PurpleAccountsGetAllActive()
        except dbus.DBusException:
            self.all_buddies = {}
            return
        is_disconnected = interface.PurpleAccountIsDisconnected
        conn_accounts = set(a for a in accounts if not is_disconnected(a))
        for buddy, pcontact in list(self.all_buddies.items()):
            if pcontact.account not in conn_accounts:
                del self.all_buddies[buddy]

    def _signing_off(self, conn):
        self.output_debug("Pidgin Signing Off", conn)
        self._remove_buddies_not_connected()
        self.mark_for_update()

    def _update_pending(self):
        """Update all buddies in the update queue"""
        interface = _create_dbus_connection()
        if interface is None:
            self._buddy_update_queue.clear()
            return
        show_offline = __kupfer_settings__["show_offline"]
        for buddy in self._buddy_update_queue:
            if show_offline or interface.PurpleBuddyIsOnline(buddy):
                self.output_debug("updating buddy", buddy)
                pcontact = self._get_pidgin_contact(interface, buddy)
                self.all_buddies[buddy] = pcontact
            else:
                self.all_buddies.pop(buddy, None)
        self._buddy_update_queue.clear()
        self.mark_for_update()

    def _buddy_needs_update(self, buddy):
        """add @buddy to the update queue"""
        if self._buddy_update_queue is not None:
            self._buddy_update_queue.add(buddy)
            self._buddy_update_timer.set(1, self._update_pending)

    def _buddy_signed_on(self, buddy):
        if buddy not in self.all_buddies:
            self._buddy_needs_update(buddy)

    def _buddy_signed_off(self, buddy):
        if buddy in self.all_buddies:
            del self.all_buddies[buddy]
            self.mark_for_update()

    def _buddy_status_changed(self, buddy, old, new):
        '''Callback when status is changed reload the entry
        which get the new status'''
        self._buddy_needs_update(buddy)

    def _install_dbus_signal(self):
        '''Add signals to pidgin when buddy goes offline or
        online to update the list'''
        try:
            session_bus = dbus.Bus()
        except dbus.DBusException:
            return

        dbus_signal_connect_weakly(session_bus, "SigningOff",
                self._signing_off, dbus_interface=IFACE_NAME)

        dbus_signal_connect_weakly(session_bus, "BuddySignedOn",
                self._buddy_signed_on, dbus_interface=IFACE_NAME)

        dbus_signal_connect_weakly(session_bus, "BuddyStatusChanged",
                self._buddy_status_changed, dbus_interface=IFACE_NAME)

        dbus_signal_connect_weakly(session_bus, "BuddySignedOff",
                self._buddy_signed_off, dbus_interface=IFACE_NAME)

    def get_items(self):
        if not self.all_buddies:
            self._get_all_buddies()
        return list(self.all_buddies.values())

    def should_sort_lexically(self):
        return True

    def get_icon_name(self):
        return 'pidgin'

    def provides(self):
        yield PidginContact
