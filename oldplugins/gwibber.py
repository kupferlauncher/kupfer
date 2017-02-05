# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Gwibber")
__kupfer_sources__ = ("HomeMessagesSource", "AccountsSource", "StreamsSource")
__kupfer_actions__ = ("SendMessage", "SendMessageBy", "SendMessageTo")
__description__ = _("Microblogging with Gwibber. Allows sending and receiving "
                    "messages from social networks like Twitter, Identi.ca etc. "
                    "Requires the package 'gwibber-service'.")
__version__ = "2011-03-04"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import time
import locale
try:
    import cjson
    json_decoder = cjson.decode
    json_encoder = cjson.encode
except ImportError:
    import json
    json_decoder = json.loads
    json_encoder = json.dumps

import dbus
# quick test is gwibber-service installed
import gwibber.microblog

from kupfer import icons
from kupfer import pretty
from kupfer import plugin_support
from kupfer.objects import Action, TextLeaf, Source, Leaf, TextSource
from kupfer.obj.objects import OpenUrl
from kupfer.weaklib import dbus_signal_connect_weakly

plugin_support.check_dbus_connection()

DBUS_GWIBBER_SERVICE = ('com.Gwibber.Service', '/com/gwibber/Service')
DBUS_GWIBBER_ACCOUNTS = ('com.Gwibber.Accounts', '/com/gwibber/Accounts')
DBUS_GWIBBER_STREAMS = ('com.Gwibber.Streams', '/com/gwibber/Streams')
DBUS_GWIBBER_MESSAGES = ('com.Gwibber.Messages', '/com/gwibber/Messages')
DBUS_GWIBBER_SEARCH = ('com.Gwibber.Search', '/com/gwibber/Search')

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        'key': 'load_limit',
        'label': _("Maximum number of messages to show"),
        'type': int,
        'value': 25,
    }
)


def _get_dbus_iface(service_objname, activate=False):
    interface = None
    sbus = dbus.SessionBus()
    service, objname = service_objname
    try:
        proxy_obj = sbus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        if activate or dbus_iface.NameHasOwner(service):
            obj = sbus.get_object(service, objname)
            if obj:
                interface = dbus.Interface(obj, service)
    except dbus.exceptions.DBusException as err:
        pretty.print_debug(err)
    return interface


def _get_messages_for_account(stream, account, transient='0'):
    conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
    if not conn:
        return
    services = json_decoder(conn.GetServices())
    conn = _get_dbus_iface(DBUS_GWIBBER_STREAMS)
    if not conn:
        return
    result = conn.Messages(stream, account, 0, '0', transient, 'time', 'desc',
            __kupfer_settings__['load_limit'])
    for msg in json_decoder(result):
        yield Message(msg['text'], msg, services[msg['service']])


def _gwibber_refresh(conn=None):
    conn = conn or _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
    if conn:
        conn.Refresh()


def _trunc_message(message):
    return message[:139] + '…' if len(message) > 140 else message


class Account(Leaf):
    def __init__(self, account, service_name, show_content=True):
        Leaf.__init__(self, account['id'], service_name)
        self._show_content = show_content
        # TRANS: Account description, similar to "John on Identi.ca"
        self._description = _("%(user)s on %(service)s") % {
                'user': account.get('site_display_name') or account['username'],
                'service': account['service']}

    def repr_key(self):
        return self.object

    def get_icon_name(self):
        return 'gwibber'

    def has_content(self):
        return self._show_content

    def content_source(self, alternate=False):
        return MessagesSource(self.object, self.name)

    def get_description(self):
        return self._description


class Stream(Leaf):
    def __init__(self, name, id_, account):
        Leaf.__init__(self, id_, name)
        self.account = account

    def repr_key(self):
        return self.object

    def get_icon_name(self):
        return 'gwibber'

    def has_content(self):
        return True

    def content_source(self, alternate=False):
        return StreamMessagesSource(self)

def unicode_strftime(fmt, time_tuple=None):
    enc = locale.getpreferredencoding(False)
    return str(time.strftime(fmt, time_tuple), enc, "replace")

class Message (Leaf):
    def __init__(self, text, msg, service):
        Leaf.__init__(self, text, text)
        self.id = msg['id']
        self.msg_url = msg.get('url')
        self.msg_sender = msg['sender']['nick'] if 'nick' in msg['sender'] \
                else msg['sender']['name']
        self._service_features = list(service['features'])
        self._is_my_msg = bool(msg['sender']['is_me'])
        sender = str(msg['sender'].get('name') or msg['sender']['nick'])
        date = unicode_strftime('%c', time.localtime(msg['time']))
        # TRANS: Gwibber Message description
        # TRANS: Similar to "John  May 5 2011 11:40 on Identi.ca"
        # TRANS: the %(user)s and similar tokens must be unchanged
        self._description = _("%(user)s %(when)s on %(where)s") % {
                'user': sender, 'when': date, 'where': service['name']}

    def repr_key(self):
        return self.id

    def get_actions(self):
        service_features = self._service_features
        if self._is_my_msg:
            if 'delete' in service_features:
                yield DeleteMessage()
        else:
            if 'reply' in service_features:
                yield Reply()
            if 'send_private' in service_features:
                yield SendPrivate()
            if 'retweet' in service_features:
                yield Retweet()
                yield Retweet(True)
        if self.msg_url:
            yield OpenMessageUrl()

    def get_description(self):
        return self._description

    def get_text_representation(self):
        return self.object

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "stock_mail")


class SendMessage(Action):
    def __init__(self):
        Action.__init__(self, _('Send Message'))

    def activate(self, leaf):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if conn:
            conn.SendMessage(_trunc_message(leaf.object))
            _gwibber_refresh()

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, item):
        return bool(item.object)

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-message-new")

    def get_description(self):
        return _("Send message to all Gwibber accounts")


class SendMessageBy(Action):
    def __init__(self):
        Action.__init__(self, _("Send Message To..."))

    def activate(self, leaf, iobj):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if conn:
            msg = {'message': _trunc_message(leaf.object), 'accounts': [iobj.object]}
            conn.Send(json_encoder(msg))
            _gwibber_refresh()

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, item):
        return bool(item.object)

    def requires_object(self):
        return True

    def object_types(self):
        yield Account

    def object_source(self, for_item=None):
        return SendToAccountSource('send')

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-message-new")

    def get_description(self):
        return _("Send message to a Gwibber account")


class SendMessageTo(Action):
    def __init__(self):
        Action.__init__(self, _("Send Message..."))

    def activate(self, leaf, iobj):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if conn:
            msg = {'message': _trunc_message(iobj.object),
                    'accounts': [leaf.object]}
            conn.Send(json_encoder(msg))
            _gwibber_refresh()

    def item_types(self):
        yield Account

    def requires_object(self):
        return True

    def object_source(self, for_item=None):
        return TextSource()

    def object_types(self):
        yield TextLeaf

    def valid_object(self, iobj, for_item=None):
        # ugly, but we don't want derived text
        return type(iobj) is TextLeaf

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-message-new")

    def get_description(self):
        return _("Send message to selected Gwibber account")


class Reply(Action):
    def __init__(self):
        Action.__init__(self, _("Reply..."))

    def activate(self, leaf, iobj):
        conn = _get_dbus_iface(DBUS_GWIBBER_MESSAGES, True)
        if not conn:
            return
        rmsg = json_decoder(conn.Get(leaf.id))
        text = '@%s: %s' % (rmsg['sender']['nick'], iobj.object)
        msg = {'message': _trunc_message(text), 'target': rmsg}
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE)
        if conn:
            conn.Send(json_encoder(msg))
            _gwibber_refresh()

    def item_types(self):
        yield Message

    def requires_object(self):
        return True

    def object_source(self, for_item=None):
        return TextSource()

    def object_types(self):
        yield TextLeaf

    def valid_object(self, iobj, for_item=None):
        # ugly, but we don't want derived text
        return type(iobj) is TextLeaf

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-reply-all")


class DeleteMessage(Action):
    def __init__(self):
        Action.__init__(self, _("Delete Message"))

    def activate(self, leaf):
        conn = _get_dbus_iface(DBUS_GWIBBER_MESSAGES, True)
        if not conn:
            return
        rmsg = json_decoder(conn.Get(leaf.id))
        cmd = {'transient': False, 'account': rmsg['account'],
                'operation': 'delete', 'args': {'message': rmsg}}
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE)
        if conn:
            conn.PerformOp(json_encoder(cmd))
            _gwibber_refresh(conn)

    def item_types(self):
        yield Message

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "stock_delete")


class SendPrivate(Action):
    def __init__(self):
        Action.__init__(self, _("Send Private Message..."))

    def activate(self, leaf, iobj):
        conn = _get_dbus_iface(DBUS_GWIBBER_MESSAGES, True)
        if not conn:
            return
        rmsg = json_decoder(conn.Get(leaf.id))
        msg = {'message': _trunc_message(iobj.object), 'private': rmsg}
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE)
        if conn:
            conn.Send(json_encoder(msg))
            _gwibber_refresh()

    def item_types(self):
        yield Message

    def requires_object(self):
        return True

    def object_source(self, for_item=None):
        return TextSource()

    def object_types(self):
        yield TextLeaf

    def valid_object(self, iobj, for_item=None):
        # ugly, but we don't want derived text
        return type(iobj) is TextLeaf

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-reply-sender")

    def get_description(self):
        return _("Send direct message to user")


class Retweet(Action):
    def __init__(self, retweet_to_all=False):
        self._retweet_to_all = retweet_to_all
        name = _("Retweet") if retweet_to_all else _("Retweet To...")
        Action.__init__(self, name)

    def activate(self, leaf, iobj=None):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if conn:
            text = '♺ @%s: %s' % (leaf.msg_sender, leaf.object)
            if iobj:
                msg = {'message': _trunc_message(text), 'accounts': [iobj.object]}
                conn.Send(json_encoder(msg))
            else:
                conn.SendMessage(_trunc_message(text))
            _gwibber_refresh()

    def item_types(self):
        yield Message

    def requires_object(self):
        return not self._retweet_to_all

    def object_types(self):
        yield Account

    def object_source(self, for_item=None):
        return SendToAccountSource('retweet')

    def get_gicon(self):
        return icons.ComposedIcon("gwibber", "mail-message-forward")

    def get_description(self):
        if self._retweet_to_all:
            return _("Retweet message to all Gwibber accounts")
        return _("Retweet message to a Gwibber account")


class OpenMessageUrl(OpenUrl):
    def __init__(self):
        OpenUrl.__init__(self, _("Open in Browser"))

    def activate(self, leaf):
        self.open_url(leaf.msg_url)

    def get_description(self):
        return _("Open message in default web browser")


class AccountsSource(Source):
    source_user_reloadable = True

    def __init__(self, name=_("Gwibber Accounts")):
        Source.__init__(self, name)

    def initialize(self):
        session_bus = dbus.Bus()
        for signal in ('Created', 'Updated', 'Deleted'):
            dbus_signal_connect_weakly(session_bus, signal,
                    self._signal_update, dbus_interface=DBUS_GWIBBER_ACCOUNTS[0])

    def _signal_update(self, *args):
        self.mark_for_update()

    def get_items(self):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if not conn:
            return
        services = json_decoder(conn.GetServices())
        del conn
        if not services:
            return
        conn = _get_dbus_iface(DBUS_GWIBBER_ACCOUNTS, True)
        if conn:
            accounts = json_decoder(conn.List())
            for account in accounts:
                service = services[account['service']]
                yield Account(account, service['name'])

    def get_icon_name(self):
        return 'gwibber'

    def get_description(self):
        return _("Accounts configured in Gwibber")

    def provides(self):
        yield Account


class SendToAccountSource(Source):
    def __init__(self, required_feature=None, name=_("Gwibber Accounts")):
        Source.__init__(self, name)
        self._required_feature = required_feature

    def get_items(self):
        conn = _get_dbus_iface(DBUS_GWIBBER_SERVICE, True)
        if not conn:
            return
        services = json_decoder(conn.GetServices())
        conn = _get_dbus_iface(DBUS_GWIBBER_ACCOUNTS, True)
        if conn:
            for account in json_decoder(conn.List()):
                aservice = account['service']
                if aservice not in services:
                    continue
                service = services[aservice]
                if not self._required_feature or \
                        self._required_feature in service['features']:
                    yield Account(account, service['name'], False)

    def get_icon_name(self):
        return 'gwibber'

    def provides(self):
        yield Account


class HomeMessagesSource(Source):
    # we don't connect to "gwibber" app as long we only need "gwibber-service".
    source_user_reloadable = True
    source_prefer_sublevel = True

    def __init__(self, name=_("Gwibber Messages")):
        Source.__init__(self, name)

    def initialize(self):
        session_bus = dbus.Bus()
        dbus_signal_connect_weakly(session_bus, 'Message',
                self._signal_update, dbus_interface=DBUS_GWIBBER_MESSAGES[0])
        dbus_signal_connect_weakly(session_bus, 'LoadingComplete',
                self._signal_update, dbus_interface=DBUS_GWIBBER_SERVICE[0])
        for signal in ('Created', 'Updated', 'Deleted'):
            dbus_signal_connect_weakly(session_bus, signal,
                    self._signal_update, dbus_interface=DBUS_GWIBBER_STREAMS[0])

    def _signal_update(self, *args):
        self.mark_for_update()

    def get_items(self):
        return _get_messages_for_account('messages', 'all')

    def get_icon_name(self):
        return 'gwibber'

    def get_description(self):
        return _("Recent messages received by Gwibber")

    def provides(self):
        yield Message


class MessagesSource(Source):
    def __init__(self, account, service):
        # TRANS:  %s is a service name
        Source.__init__(self, _("Gwibber Messages for %s") % service)
        self.account = account

    def get_items(self):
        return _get_messages_for_account('messages', self.account)

    def get_icon_name(self):
        return 'gwibber'

    def provides(self):
        yield Message


class StreamsSource(Source):
    source_user_reloadable = True

    def __init__(self, name=_("Gwibber Streams")):
        Source.__init__(self, name)

    def initialize(self):
        session_bus = dbus.Bus()
        for signal in ('Created', 'Updated', 'Deleted'):
            dbus_signal_connect_weakly(session_bus, signal,
                    self._signal_update, dbus_interface=DBUS_GWIBBER_STREAMS[0])
        _gwibber_refresh()

    def _signal_update(self, *args):
        self.mark_for_update()

    def get_items(self):
        conn = _get_dbus_iface(DBUS_GWIBBER_STREAMS, True)
        if conn:
            for stream in json_decoder(conn.List()):
                yield Stream(stream['name'], stream['id'], stream['account'])

    def get_icon_name(self):
        return 'gwibber'

    def get_description(self):
        return _("Streams configured in Gwibber")

    def provides(self):
        yield Stream

class StreamMessagesSource(Source):
    def __init__(self, stream):
        # TRANS: Gwibber messages in %s :: %s is a Stream name
        Source.__init__(self, _("Gwibber Messages in %s") % stream.name)
        self._account = stream.account
        self._stream_id = stream.object

    def get_items(self):
        conn = _get_dbus_iface(DBUS_GWIBBER_STREAMS, True)
        if conn:
            return _get_messages_for_account('all', self._account, self._stream_id)

    def get_icon_name(self):
        return 'gwibber'

    def provides(self):
        yield Message


