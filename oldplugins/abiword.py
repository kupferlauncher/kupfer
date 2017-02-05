__kupfer_name__ = _("Abiword")
__kupfer_sources__ = ("RecentsSource", )
__description__ = _("Recently used documents in Abiword")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import xml.etree.cElementTree as ElementTree

import gio

from kupfer.objects import Source, FileLeaf, UrlLeaf
from kupfer.obj.helplib import PicklingHelperMixin
from kupfer.obj.apps import AppLeafContentMixin

def get_abiword_files(xmlpth, application="abiword"):
    """
    Yield URLs to abiword's recent files from XML file @xmlpth
    """
    inside = False
    for event, entry in ElementTree.iterparse(xmlpth, events=("start", "end")):
        if entry.tag == "AbiPreferences" and entry.get("app") == application:
            if event == "start":
                inside = True
        elif not inside and event != "end":
            continue
        if entry.tag == "Recent":
            return (entry.get(a) for a in entry.attrib if a.startswith("name"))

class RecentsSource (AppLeafContentMixin, Source, PicklingHelperMixin):
    appleaf_content_id = "abiword"
    def __init__(self, name=None):
        if not name:
            name = _("Abiword Recent Items")
        super(RecentsSource, self).__init__(name)
        self.unpickle_finish()

    def pickle_prepare(self):
        # monitor is not pickleable
        self.monitor = None

    def unpickle_finish(self):
        """Set up change monitor"""
        abifile = self._get_abiword_file()
        if not abifile: return
        gfile = gio.File(abifile)
        self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE, None)
        if self.monitor:
            self.monitor.connect("changed", self._changed)

    def _changed(self, monitor, file1, file2, evt_type):
        """Change callback; something changed"""
        if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
                gio.FILE_MONITOR_EVENT_DELETED,
                gio.FILE_MONITOR_EVENT_CHANGED):
            self.mark_for_update()

    def _get_abiword_file(self):
        abifile = os.path.expanduser("~/.AbiSuite/AbiWord.Profile")
        if not os.path.exists(abifile):
            return None
        return abifile

    def get_items(self):
        abifile = self._get_abiword_file()
        if not abifile:
            self.output_debug("Abiword profile not found at", abifile)
            return

        try:
            uris = list(get_abiword_files(abifile))
        except EnvironmentError as exc:
            self.output_error(exc)
            return

        for uri in uris:
            gfile = gio.File(uri)
            if not gfile.query_exists():
                continue

            if gfile.get_path():
                leaf = FileLeaf(gfile.get_path())
            else:
                leaf = UrlLeaf(gfile.get_uri(), gfile.get_basename())
            yield leaf

    def get_description(self):
        return _("Recently used documents in Abiword")

    def get_icon_name(self):
        return "document-open-recent"
    def provides(self):
        yield FileLeaf
        yield UrlLeaf

