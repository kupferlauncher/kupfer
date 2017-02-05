__kupfer_name__ = _("Chromium Bookmarks")
__kupfer_sources__ = ("BookmarksSource", )
__description__ = _("Index of Chromium bookmarks")
__version__ = ""
__author__ = "Francesco Marella <francesco.marella@gmail.com>"

from kupfer.objects import Source
from kupfer.objects import UrlLeaf
from kupfer import config
from kupfer.obj.apps import AppLeafContentMixin


class BookmarksSource (AppLeafContentMixin, Source):
    appleaf_content_id = ("chromium-browser")
    def __init__(self):
        super(BookmarksSource, self).__init__(_("Chromium Bookmarks"))

    def _get_chromium_items(self, fpath):
        """Parse Chromium' bookmarks backups"""
        from kupfer.plugin import chromium_support
        self.output_debug("Parsing", fpath)
        bookmarks = chromium_support.get_bookmarks(fpath)
        for book in bookmarks:
            yield UrlLeaf(book["url"], book["name"])

    def get_items(self):
        fpath = config.get_config_file("Bookmarks", package="chromium/Default")

        # If there is no chromium bookmarks file, look for a google-chrome one
        if not fpath:
            fpath = config.get_config_file("Bookmarks",package="google-chrome/Default")

        if fpath:
            try:
                return self._get_chromium_items(fpath)
            except Exception as exc:
                self.output_error(exc)

        self.output_error("No Chromium bookmarks file found")
        return []

    def get_description(self):
        return _("Index of Chromium bookmarks")
    def get_icon_name(self):
        return "chromium-browser"
    def provides(self):
        yield UrlLeaf
