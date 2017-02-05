# -*- coding: UTF-8 -*-


__kupfer_name__ = _("Terminal Server Client")
__kupfer_sources__ = ("TsclientSessionSource", )
__kupfer_actions__ = ("TsclientOpenSession", )
__description__ = _("Session saved in Terminal Server Client")
__version__ = "2010-10-01"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Changes:
2010-10-01
    Freddie Brandt
    - read files in subdirs ~/.tsclient
    Karol:
    - drop FilesystemWatchMixin, add source_user_reloadable
'''

import os

from kupfer.objects import Action
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import utils, icons
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.hosts import HOST_NAME_KEY, HostLeaf


TSCLIENT_SESSION_KEY = "TSCLIENT_SESSION"


class TsclientSession(HostLeaf):
    """ Leaf represent session saved in Tsclient"""

    def __init__(self, obj_path, name, description):
        slots = {HOST_NAME_KEY: name, TSCLIENT_SESSION_KEY: obj_path}
        HostLeaf.__init__(self, slots, name)
        self._description = description

    def get_description(self):
        return self._description

    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "tsclient")


class TsclientOpenSession(Action):
    ''' opens tsclient session '''
    def __init__(self):
        Action.__init__(self, _('Start Session'))

    def activate(self, leaf):
        session = leaf[TSCLIENT_SESSION_KEY]
        utils.spawn_async(["tsclient", "-x", session])

    def get_icon_name(self):
        return 'tsclient'

    def item_types(self):
        yield HostLeaf

    def valid_for_item(self, item):
        return item.check_key(TSCLIENT_SESSION_KEY)


class TsclientSessionSource(AppLeafContentMixin, ToplevelGroupingSource):
    ''' indexes session saved in tsclient '''

    appleaf_content_id = 'tsclient'
    source_user_reloadable = True

    def __init__(self, name=_("TSClient sessions")):
        ToplevelGroupingSource.__init__(self, name, "hosts")
        self._sessions_dir = os.path.expanduser('~/.tsclient')
        self._version = 2

    def initialize(self):
        ToplevelGroupingSource.initialize(self)

    def get_items(self):
        if not os.path.isdir(self._sessions_dir):
            return
        for root, sub_folders_, files in os.walk(self._sessions_dir):
            for filename in files:
                if not filename.endswith('.rdp'):
                    continue
                obj_path = os.path.join(root, filename)
                if os.path.isfile(obj_path):
                    name = filename[:-4]
                    description = self._load_descr_from_session_file(obj_path)
                    yield TsclientSession(obj_path, name, description)

    def get_description(self):
        return _("Saved sessions in Terminal Server Client")

    def get_icon_name(self):
        return "tsclient"

    def provides(self):
        yield TsclientSession

    def _load_descr_from_session_file(self, filepath):
        user = None
        host = None
        try:
            with open(filepath, 'r') as session_file:
                for line in session_file:
                    if line.startswith('full address:s:'):
                        host = line.split(':s:', 2)[1].strip()
                    elif line.startswith('username:s:'):
                        user = line.split(':s:', 2)[1].strip()
        except IOError as err:
            self.output_error(err)
        else:
            if host:
                return str(user + '@' + host if user else host, "UTF-8",
                        "replace")
        return 'Terminal Server Client Session'
