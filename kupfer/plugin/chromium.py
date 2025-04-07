from __future__ import annotations

__kupfer_name__ = _("Chromium Bookmarks")
__kupfer_sources__ = ("BookmarksSource",)
__description__ = _("Index of Chromium bookmarks")
__version__ = ""
__author__ = "Francesco Marella <francesco.marella@gmail.com>"

import typing as ty

from kupfer import config, plugin_support
from kupfer.obj import Source, UrlLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FileMonitorToken, FilesystemWatchMixin
from kupfer.plugin import chromium_support

if ty.TYPE_CHECKING:
    from gettext import gettext as _


plugin_support.check_any_command_available("chromium", "chromium-browser")


def _get_chrome_conf_filepath() -> str | None:
    fpath = config.get_config_file("Bookmarks", package="chromium/Default")

    # If there is no chromium bookmarks file, look for a google-chrome one
    if not fpath:
        fpath = config.get_config_file(
            "Bookmarks", package="google-chrome/Default"
        )

    return fpath


class BookmarksSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("chromium-browser", "chromium")
    source_scan_interval: int = 3600

    def __init__(self) -> None:
        self.monitor_token: FileMonitorToken | None = None
        super().__init__(_("Chromium Bookmarks"))

    def initialize(self) -> None:
        if fpath := _get_chrome_conf_filepath():
            self.monitor_token = self.monitor_directories(fpath)

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_basename() == "lock"

    def mark_for_update(self, postpone=False):
        super().mark_for_update(postpone=True)

    def _get_chromium_items(self, fpath: str) -> ty.Iterator[UrlLeaf]:
        """Parse Chromium' bookmarks backups"""
        self.output_debug("Parsing", fpath)
        bookmarks = chromium_support.get_bookmarks(fpath)
        for book in bookmarks:
            yield UrlLeaf(book["url"], book["name"])

    def get_items(self) -> ty.Iterable[UrlLeaf]:
        if fpath := _get_chrome_conf_filepath():
            try:
                return self._get_chromium_items(fpath)
            except Exception as exc:
                self.output_error(exc)

        self.output_error("No Chromium bookmarks file found")
        return ()

    def get_description(self):
        return _("Index of Chromium bookmarks")

    def get_icon_name(self):
        return "chromium-browser"

    def provides(self):
        yield UrlLeaf
