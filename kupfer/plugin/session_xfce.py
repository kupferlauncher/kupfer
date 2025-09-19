from __future__ import annotations

__kupfer_name__ = _("XFCE Session Management")
__kupfer_sources__ = ("XfceItemsSource", "XfceWhskerFavoritesSource")
__description__ = _("Special items and actions for XFCE environment")
__version__ = "2025-09-19"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import typing as ty
import xml.parsers
from itertools import chain
from pathlib import Path
from xml.dom import minidom

from kupfer import plugin_support, puid
from kupfer.core import learn
from kupfer.obj import Leaf, Source
from kupfer.plugin import session_support as support
from kupfer.support import pretty

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "lock_cmd",
        "label": _("Screen lock command"),
        "type": str,
        "value": "xflock4",
    },
    {
        "key": "whisker_favs",
        "label": _("Load Whisker Menu Favorite applications"),
        "type": bool,
        "value": True,
    },
)

# sequences of argument lists
_LOGOUT_CMD = (["xfce4-session-logout", "--logout"],)
_SHUTDOWN_CMD = (["xfce4-session-logout"],)


class XfceItemsSource(support.CommonSource):
    source_scan_interval: int = 36000

    def __init__(self):
        support.CommonSource.__init__(self, _("XFCE Session Management"))

    def get_items(self):
        lockscreen_cmd = (
            __kupfer_settings__["lock_cmd"] or "xdg-screensaver lock"
        )

        return (
            support.Logout(_LOGOUT_CMD),
            support.LockScreen((lockscreen_cmd.split(" "),)),
            support.Shutdown(_SHUTDOWN_CMD),
        )


def _find_whisher_conf_file() -> Path | None:
    base = Path("~/.config/xfce4/panel/").expanduser()
    files = (f for f in base.glob("whiskermenu*.rc") if f.is_file())
    sorted_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
    return sorted_files[0] if sorted_files else None


def _get_whisker_conf_favs() -> list[str]:
    # find most recent configuration file
    conf_file = _find_whisher_conf_file()
    if not conf_file:
        return []

    pretty.print_debug(__name__, "loading whisker rc file", conf_file)

    with open(conf_file, encoding="UTF-8") as conf:
        for line in conf:
            if not line.startswith("favorites="):
                continue

            *_pref, favs = line.strip().partition("=")
            return favs.split(",")

    return []


def _load_whisher_favs_new() -> ty.Iterable[str]:
    panel_conf = Path(
        "~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"
    ).expanduser()

    try:
        dtree = minidom.parse(str(panel_conf))
        for prop in dtree.getElementsByTagName("property"):
            if prop.getAttribute("value") != "whiskermenu":
                continue

            for cc in prop.childNodes:
                if (
                    isinstance(cc, minidom.Element)
                    and cc.tagName == "property"
                    and cc.getAttribute("name") == "favorites"
                ):
                    return (
                        v.getAttribute("value")
                        for v in cc.getElementsByTagName("value")
                    )
    except (Exception, xml.parsers.expat.ExpatError) as err:
        pretty.print_error(__name__, "parse", panel_conf, "error", err)

    return ()


def _load_whisher_favs() -> ty.Iterator[Leaf]:
    # simplified version
    for fav in chain(_get_whisker_conf_favs(), _load_whisher_favs_new()):
        name, *_rest = fav.rpartition(".")
        id_ = f"<kupfer.obj.apps.AppLeaf {name}>"
        # ignore invalid objects
        if (
            (itm := puid.resolve_unique_id(id_))
            and (not hasattr(itm, "is_valid") or itm.is_valid())
            and isinstance(itm, Leaf)
        ):
            yield itm


class XfceWhskerFavoritesSource(Source):
    source_scan_interval: int = 1800
    serializable = None

    def __init__(self):
        Source.__init__(self, _("Whisker Favorites"))

    def initialize(self):
        self.mark_for_update()

    def finalize(self) -> None:
        learn.replace_favorites(__name__)

    def get_items(self):
        if not __kupfer_settings__["whisker_favs"]:
            return []

        try:
            favs = list(_load_whisher_favs())
        except OSError:
            favs = []
        else:
            learn.replace_favorites(__name__, *favs)

        return favs

    def get_description(self):
        return _("Favorite items from Xfce Whisker Menu")

    def get_icon_name(self):
        return "emblem-favorite"

    def is_valid(self):
        # for future use
        return __kupfer_settings__["whisker_favs"]
