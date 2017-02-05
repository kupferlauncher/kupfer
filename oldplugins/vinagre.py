# -*- coding: UTF-8 -*-


__kupfer_name__ = _("Vinagre")
__kupfer_sources__ = ("SessionSource", )
__kupfer_actions__ = ('VinagreStartSession', )
__description__ = _("Vinagre bookmarks and actions")
__version__ = "2009-11-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


import os
import gio
from xml.etree import cElementTree as ElementTree

from kupfer.objects import Action, UrlLeaf
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import utils, icons
from kupfer.obj.grouping import ToplevelGroupingSource 
from kupfer.obj.hosts import HostServiceLeaf, HOST_ADDRESS_KEY, \
        HOST_SERVICE_NAME_KEY, HOST_SERVICE_PORT_KEY, HOST_SERVICE_USER_KEY

BOOKMARKS_FILE = '~/.local/share/vinagre/vinagre-bookmarks.xml'


class Bookmark(HostServiceLeaf):
    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "vinagre")


class VinagreStartSession(Action):
    def __init__(self):
        Action.__init__(self, _('Start Vinagre Session'))

    def activate(self, leaf):
        if isinstance(leaf, UrlLeaf):
            utils.spawn_async(["vinagre", leaf.object])
        else:
            service = leaf[HOST_SERVICE_NAME_KEY]
            host = leaf[HOST_ADDRESS_KEY]
            port = ''
            if leaf.check_key(HOST_SERVICE_PORT_KEY):
                port = ':' + leaf[HOST_SERVICE_PORT_KEY]
            user = ''
            if leaf.check_key(HOST_SERVICE_USER_KEY):
                user = leaf[HOST_SERVICE_USER_KEY] + '@'
            url = '%s://%s%s%s' % (service, user, host, port)
            utils.spawn_async(["vinagre", url])

    def get_icon_name(self):
        return 'vinagre'

    def item_types(self):
        yield HostServiceLeaf
        yield UrlLeaf

    def valid_for_item(self, item):
        if isinstance(item, HostServiceLeaf):
            if item.check_key(HOST_SERVICE_NAME_KEY):
                service = item[HOST_SERVICE_NAME_KEY]
                return service in ('ssh', 'vnc')
            return False
        return (item.object.startswith('ssh://') \
                or item.object.startswith('vnc://'))


class SessionSource(AppLeafContentMixin, ToplevelGroupingSource,
        PicklingHelperMixin):
    appleaf_content_id = 'vinagre'

    def __init__(self, name=_("Vinagre Bookmarks")):
        ToplevelGroupingSource.__init__(self, name, 'hosts')
        self._version = 2

    def pickle_prepare(self):
        self.monitor = None

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        bookmark_file = os.path.expanduser(BOOKMARKS_FILE)
        gfile = gio.File(bookmark_file)
        self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
        if self.monitor:
            self.monitor.connect("changed", self._on_bookmarks_changed)

    def _on_bookmarks_changed(self, monitor, file1, file2, evt_type):
        if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
                gio.FILE_MONITOR_EVENT_DELETED,
                gio.FILE_MONITOR_EVENT_CHANGED):
            self.mark_for_update()

    def get_items(self):
        bookmark_file = os.path.expanduser(BOOKMARKS_FILE)
        if not os.path.isfile(bookmark_file):
            return

        try:
            tree = ElementTree.parse(bookmark_file)
            for item in tree.findall('item'):
                protocol = item.find('protocol').text
                name = item.find('name').text
                host = item.find('host').text
                port = item.find('port').text
                url = '%s://%s:%s' % (protocol, host, port)
                user = None
                if host.find('@') > 0:
                    user, host = host.split('@', 1)
                yield Bookmark(name, host, protocol, url, port, user)
        except Exception as err:
            self.output_error(err)

    def get_description(self):
        return None

    def get_icon_name(self):
        return "vinagre"

    def provides(self):
        yield Bookmark


