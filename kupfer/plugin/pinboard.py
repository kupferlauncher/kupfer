__kupfer_name__ = _("Pinboard")
__kupfer_sources__ = ("PinboardBookmarkSource",)
__kupfer_actions__ = ()
__description__ = _("Manage and use bookmarks from Pinboard")
__version__ = "2020-11-15"
__author__ = "Peter Stuifzand <peter@p83.nl>"

import pinboard  # pylint: disable=import-error

from kupfer import plugin_support
from kupfer.obj import Source, UrlLeaf

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "token",
        "label": _("Pinboard API Token"),
        "type": str,
        "value": "",
    },
)


class PinboardBookmarkSource(Source):
    def __init__(self):
        super().__init__(_("Pinboard Bookmarks"))

    def get_items(self):
        token = __kupfer_settings__["token"]
        if token == "":
            return []

        pinb = pinboard.Pinboard(token)
        bookmarks = pinb.posts.all(start=0, results=100)
        return [UrlLeaf(b.url, b.description) for b in bookmarks]

    def get_description(self):
        return _("Index of Pinboard bookmarks")

    def get_gicon(self):
        if lrepr := self.get_leaf_repr():
            return lrepr.get_gicon()

        return None

    def get_icon_name(self):
        return "web-browser"

    def provides(self):
        yield UrlLeaf
