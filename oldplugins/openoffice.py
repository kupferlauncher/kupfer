# -*- coding: UTF-8 -*-

__kupfer_name__ = _("OpenOffice / LibreOffice")
__kupfer_sources__ = ("RecentsSource", )
__description__ = _("Recently used documents in OpenOffice/LibreOffice")
__version__ = "2011-04-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Changes:
    2011-04-02: Support new cofiguration file format in LibreOffice.
'''

import os
from xml.etree import cElementTree as ElementTree
import gio

from kupfer.objects import Source, FileLeaf, UrlLeaf, AppLeaf
from kupfer.obj.helplib import FilesystemWatchMixin


_HISTORY_FILE = [
        "~/.config/libreoffice/3/user/registrymodifications.xcu",
        "~/.libreoffice/3/user/registrymodifications.xcu",
        "~/.openoffice.org/3/user/registrymodifications.xcu",
        "~/.openoffice.org/3/user/registry/data/org/openoffice/Office/Histories.xcu",
]
_NAME_ATTR = "{http://openoffice.org/2001/registry}name"
_PATH_ATTR = "{http://openoffice.org/2001/registry}path"
_HISTORY_NODES = "/org.openoffice.Office.Histories/Histories/" \
        "org.openoffice.Office.Histories:HistoryInfo['PickList']/OrderList"


class MultiAppContentMixin (object):
    """
    Mixin for Source that decorates many app leaves

    This Mixin sees to that the Source is set as content for the applications
    with id 'cls.appleaf_content_id', which may also be a sequence of ids.

    Source has to define the attribute appleaf_content_id and must
    inherit this mixin BEFORE the Source

    This Mixin defines:
    decorates_type,
    decorates_item
    """
    @classmethod
    def __get_appleaf_id_iter(cls):
        if hasattr(cls.appleaf_content_id, "__iter__"):
            ids = iter(cls.appleaf_content_id)
        else:
            ids = (cls.appleaf_content_id, )
        return ids

    @classmethod
    def decorates_type(cls):
        return AppLeaf

    @classmethod
    def decorate_item(cls, leaf):
        if leaf.get_id() in cls.__get_appleaf_id_iter():
            return cls()


class RecentsSource (MultiAppContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = [
            "openoffice.org-writer",
            "openoffice.org-base",
            "openoffice.org-calc",
            "openoffice.org-draw",
            "openoffice.org-impress",
            "openoffice.org-math",
            "openoffice.org-startcenter",
            "libreoffice-writer",
            "libreoffice-base",
            "libreoffice-calc",
            "libreoffice-draw",
            "libreoffice-impress",
            "libreoffice-math",
            "libreoffice-startcenter",
    ]

    def __init__(self, name=_("OpenOffice/LibreOffice Recent Items")):
        Source.__init__(self, name)

    def initialize(self):
        hist_file_path = _get_history_files()
        if hist_file_path:
            dirs = list(map(os.path.dirname, hist_file_path))
            self.monitor_token = self.monitor_directories(*dirs)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename().endswith('.xcu')

    def get_items(self):
        for hist_file_path in _get_history_files():
            self.output_debug('reading', hist_file_path)
            try:
                tree = ElementTree.parse(hist_file_path)
                node_histories = tree.find('node')
                if node_histories and node_histories.attrib[_NAME_ATTR] == 'Histories':
                    for list_node in  node_histories.findall('node'):
                        if list_node.attrib[_NAME_ATTR] == 'PickList':
                            items_node = list_node.find('node')
                            if (not items_node \
                                    or items_node.attrib[_NAME_ATTR] != 'ItemList'):
                                return
                            for node in items_node.findall('node'):
                                hfile = node.attrib[_NAME_ATTR]  # file://.....
                                leaf = _create_history_leaf(hfile)
                                if leaf:
                                    yield leaf
                            break
                #  new configuration file
                for item in tree.getroot().findall('item'):
                    if item.get(_PATH_ATTR) != _HISTORY_NODES:
                        continue
                    node = item.find('node')
                    if not node:
                        continue
                    prop = node.find('prop')
                    if not prop:
                        continue
                    if prop.get(_NAME_ATTR) != 'HistoryItemRef':
                        continue
                    value = prop.find('value')
                    if value is not None:
                        leaf = _create_history_leaf(value.text)
                        if leaf:
                            yield leaf
            except Exception as err:
                self.output_error(err)

    def get_description(self):
        return _("Recently used documents in OpenOffice/LibreOffice")

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf
        yield UrlLeaf


def _get_history_files():
    ''' get all existing files with history '''
    for file_path in _HISTORY_FILE:
        path = os.path.expanduser(file_path)
        if os.path.isfile(path):
            yield path


def _create_history_leaf(path):
    ''' Create leaf from file url '''
    if not path:
        return None
    gfile = gio.File(path)
    if not gfile.query_exists():
        None
    if gfile.get_path():
        return FileLeaf(gfile.get_path())
    return UrlLeaf(path, gfile.get_basename())
