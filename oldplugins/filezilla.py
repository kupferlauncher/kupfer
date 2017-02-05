# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Filezilla")
__kupfer_sources__ = ("SitesSource", )
__kupfer_actions__ = ('OpeninFilezilla', )
__description__ = _("Show sites and handle ftp addresses by Filezilla")
__version__ = "2010-04-13"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
from xml.etree import cElementTree as ElementTree

from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.base import Action
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.objects import UrlLeaf, TextLeaf
from kupfer.obj import hosts
from kupfer import utils, icons


_SITEMANAGER_DIR = os.path.expanduser("~/.filezilla/")
_SITEMANAGER_FILE = "sitemanager.xml"
FILEZILLA_SITE_KEY = "FILEZILLA_SITE"


class Site(hosts.HostServiceLeaf):
    def __init__(self, name, host, descr, port, user, passwd, remotedir,
            entry_type):
        slots = {FILEZILLA_SITE_KEY: name,
                hosts.HOST_SERVICE_REMOTE_PATH_KEY: remotedir}
        hosts.HostServiceLeaf.__init__(self, name, host, 'ftp', descr, port,
                user, passwd, slots)
        self.entry_type = entry_type

    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "filezilla")


class OpeninFilezilla(Action):
    def __init__(self):
        Action.__init__(self, _("Open Site with Filezilla"))

    def activate(self, leaf, iobj=None):
        if isinstance(leaf, (UrlLeaf, TextLeaf)):
            utils.spawn_async(['filezilla', leaf.object])
        elif leaf.check_key(FILEZILLA_SITE_KEY):
            sessname = leaf.entry_type + '/' + leaf[hosts.HOST_NAME_KEY]
            utils.spawn_async(['filezilla', '-c', sessname])
        else:
            url = ['ftp://']
            if leaf.check_key(hosts.HOST_SERVICE_USER_KEY):
                url.append(leaf[hosts.HOST_SERVICE_USER_KEY])
                if leaf.check_key(hosts.HOST_SERVICE_PASS_KEY):
                    url.append(':')
                    url.append(leaf[hosts.HOST_SERVICE_PASS_KEY])
                url.append('@')
            url.append(leaf[hosts.HOST_ADDRESS_KEY])
            if leaf.check_key(hosts.HOST_SERVICE_PORT_KEY):
                url.append(':')
                url.append(leaf[hosts.HOST_SERVICE_PORT_KEY])
            if leaf.check_key(hosts.HOST_SERVICE_REMOTE_PATH_KEY):
                url.append(leaf[hosts.HOST_SERVICE_REMOTE_PATH_KEY])
            utils.spawn_async(['filezilla', ''.join(url)])

    def get_icon_name(self):
        return "filezilla"

    def item_types(self):
        yield hosts.HostLeaf
        yield UrlLeaf
        yield TextLeaf

    def valid_for_item(self, item):
        if isinstance(item, (UrlLeaf, TextLeaf)):
            return item.object.startswith('ftp')
        if item.check_key(hosts.HOST_SERVICE_NAME_KEY):
            if item[hosts.HOST_SERVICE_NAME_KEY] == 'ftp':
                return True
        return item.check_key(FILEZILLA_SITE_KEY)


class SitesSource (AppLeafContentMixin, ToplevelGroupingSource,
        FilesystemWatchMixin):
    appleaf_content_id = "filezilla"

    def __init__(self, name=_("Filezilla Sites")):
        ToplevelGroupingSource.__init__(self, name, "hosts")

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        self.monitor_token = self.monitor_directories(_SITEMANAGER_DIR)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == _SITEMANAGER_FILE

    def get_items(self):
        sm_file_path = os.path.join(_SITEMANAGER_DIR, _SITEMANAGER_FILE)
        if not os.path.isfile(sm_file_path):
            return
        try:
            tree = ElementTree.parse(sm_file_path)
            for server in tree.find('Servers').findall('Server'):
                host = get_xml_element_text(server, 'Host')
                if not host:
                    continue
                port = get_xml_element_text(server, 'Port')
                etype = get_xml_element_text(server, 'Type')
                user = get_xml_element_text(server, 'User')
                passwd = get_xml_element_text(server, 'Pass')
                name = get_xml_element_text(server, 'Name')
                descr = get_xml_element_text(server, 'Comments')
                remote = get_xml_element_text(server, 'RemoteDir')
                if not descr:
                    descr = '%s@%s' % (user, host) if user else host

                yield Site(name, host, descr, port, user, passwd, remote, etype)
        except Exception as err:
            self.output_error(err)

    def get_description(self):
        return _("Sites from Filezilla")

    def get_icon_name(self):
        return "filezilla"

    def provides(self):
        yield Site


def get_xml_element_text(node, tag):
    '''Find @tag in childs of @node and return text from it.
    If @tag is not found - return None'''
    child = node.find(tag)
    if child is None:
        return None
    return child.text
