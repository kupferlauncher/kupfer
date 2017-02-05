__kupfer_name__ = _("Epiphany Bookmarks")
__kupfer_sources__ = ("EpiphanySource", )
__description__ = _("Index of Epiphany bookmarks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

from kupfer.objects import Source
from kupfer.objects import UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin

from kupfer.plugin import epiphany_support

class EpiphanySource (AppLeafContentMixin, Source):
    appleaf_content_id = "epiphany"
    def __init__(self):
        super(EpiphanySource, self).__init__(_("Epiphany Bookmarks"))
    
    def get_items(self):
        fpath = os.path.expanduser(epiphany_support.EPHY_BOOKMARKS_FILE)
        if not os.path.exists(fpath):
            self.output_debug("Epiphany bookmarks file not found:", fpath)
            return ()

        try:
            bookmarks = list(epiphany_support.parse_epiphany_bookmarks(fpath))
        except EnvironmentError as exc:
            self.output_error(exc)
            return ()

        return (UrlLeaf(href, title) for title, href in bookmarks)

    def get_description(self):
        return _("Index of Epiphany bookmarks")

    def get_icon_name(self):
        return "web-browser"
    def provides(self):
        yield UrlLeaf

