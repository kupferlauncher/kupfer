# -*- coding: UTF-8 -*-

__kupfer_name__ = _("TrueCrypt")
__kupfer_sources__ = ("VolumeSource", )
__kupfer_actions__ = ('DismountAll', 'MountFile')
__description__ = _("Volumes from TrueCrypt history")
__version__ = "2009-11-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
from xml.etree import cElementTree as ElementTree
import gio

from kupfer.objects import (Action, Source, Leaf,AppLeaf, FileLeaf)
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer import utils



_HISTORY_FILE = "~/.TrueCrypt/History.xml"


def mount_volume_in_truecrypt(filepath):
    ''' Mount file in Truecrypt. 
        Escape apostrophes - ie:
        "test'dk 'dlk' dsl''k '' sdkl.test" ->
        "'test'\''dk '\''dlk'\'' dsl'\'''\''k '\'''\'' sdkl.test'"
    '''
    # escape ' characters
    filepath = filepath.replace("'", "'\\''")
    utils.spawn_async(["truecrypt", filepath])


class Volume(Leaf):
    def __init__(self, path, name):
        Leaf.__init__(self, path, name)

    def get_icon_name(self):
        return "truecrypt"

    def get_description(self):
        dispname = utils.get_display_path_for_bytestring(self.object)
        return _("TrueCrypt volume: %(file)s") % dict(file=dispname)

    def get_actions(self):
        yield MountVolume()


class MountVolume(Action):
    def __init__(self):
        Action.__init__(self, _("Mount Volume"))
        
    def activate(self, leaf):
        mount_volume_in_truecrypt(leaf.object)


class MountFile(Action):
    ''' Mount selected file in truecrypt. '''
    rank_adjust = -10

    def __init__(self):
        Action.__init__(self, _("Mount in Truecrypt"))

    def activate(self, leaf):
        mount_volume_in_truecrypt(leaf.object)

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Try to mount file as Truecrypt volume")

    def valid_for_item(self, item):
        return os.path.isfile(item.object)


class DismountAll(Action):
    def __init__(self):
        Action.__init__(self, _("Dismount All Volumes"))

    def activate(self, leaf, iobj=None):
        utils.spawn_async(['truecrypt', '-d'])

    def get_icon_name(self):
        return "hdd_unmount"

    def item_types(self):
        yield AppLeaf

    def valid_for_item(self, leaf):
        return leaf.get_id() == 'truecrypt'


class VolumeSource (AppLeafContentMixin, Source, PicklingHelperMixin):
    appleaf_content_id = "truecrypt"

    def __init__(self, name=_("TrueCrypt Volumes")):
        Source.__init__(self, name)
        self.unpickle_finish()

    def pickle_prepare(self):
        self.monitor = None

    def unpickle_finish(self):
        hist_file_path = _get_history_file_path()
        if not hist_file_path:
            return
        gfile = gio.File(hist_file_path)
        self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
        if self.monitor:
            self.monitor.connect("changed", self._on_history_changed)

    def _on_history_changed(self, monitor, file1, file2, evt_type):
        if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
                gio.FILE_MONITOR_EVENT_DELETED,
                gio.FILE_MONITOR_EVENT_CHANGED):
            self.mark_for_update()

    def get_items(self):
        hist_file_path = _get_history_file_path()
        if not hist_file_path:
            return
        
        try:
            tree = ElementTree.parse(hist_file_path)
            for volume in tree.find('history').findall('volume'):
                volume_path = volume.text
                if volume_path:
                    gfile = gio.File(volume_path)
                    if not gfile.query_exists():
                        continue
                    
                    yield Volume(gfile.get_path(), gfile.get_basename())

        except Exception as err:
            self.output_error(err)

    def get_description(self):
        return _("Volumes from TrueCrypt history")

    def get_icon_name(self):
        return "truecrypt"

    def provides(self):
        yield Volume


def _get_history_file_path():
    path = os.path.expanduser(_HISTORY_FILE)
    return path if os.path.isfile(path) else None

