from __future__ import annotations

__kupfer_name__ = _("Documents")
__kupfer_sources__ = ("RecentsSource", "PlacesSource", "IgnoredApps")
__kupfer_actions__ = ("Toggle",)
__kupfer_contents__ = ("ApplicationRecentsSource",)
__description__ = _("Recently used documents and bookmarked folders")
__version__ = "2017.3"
__author__ = ""

import functools
import typing as ty
from os import path
from pathlib import Path

import xdg.BaseDirectory as base
from gi.repository import Gio, Gtk

from kupfer import icons, launch, plugin_support
from kupfer.obj import Action, AppLeaf, FileLeaf, Source, SourceLeaf, UrlLeaf
from kupfer.support import weaklib, datatools

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "max_days",
        "label": _("Max recent document days"),
        "type": int,
        "value": 28,
    },
    {
        "key": "check_doc_exist",
        "label": _("Show only existing documents"),
        "type": bool,
        "value": True,
    },
)

ALIASES = {
    "libreoffice": "soffice",
}

# Libreoffice doesn't separate them out, so we'll hack that in manually
SEPARATE_APPS = {
    "libreoffice": {
        ".doc": "libreoffice-writer",
        ".docx": "libreoffice-writer",
        ".odt": "libreoffice-writer",
        ".ods": "libreoffice-calc",
        ".xlsx": "libreoffice-calc",
        ".csv": "libreoffice-calc",
        ".odp": "libreoffice-impress",
        ".ppt": "libreoffice-impress",
        ".pptx": "libreoffice-impress",
        ".odg": "libreoffice-draw",
        ".odf": "libreoffice-math",
        ".mml": "libreoffice-math",
    }
}


def _file_path(uri: str) -> str | None:
    try:
        return ty.cast(str, Gio.File.new_for_uri(uri).get_path())
    except Exception:
        return None


@datatools.simple_cache
def _get(
    max_days: int, check_doc_exist: bool
) -> list[tuple[str, int, tuple[str, ...]]]:
    manager = Gtk.RecentManager.get_default()
    items = []
    for item in manager.get_items():
        if item.get_age() > max_days >= 0:
            continue

        if check_doc_exist and not item.exists():
            continue

        if item.get_private_hint():
            continue

        if not item.is_local():
            continue

        uri = item.get_uri()
        if file_path := _file_path(uri):
            apps_name = tuple(_get_app_id(item))
            items.append((file_path, item.get_modified(), apps_name))

    return items


def _get_app_id(item: Gtk.RecentInfo) -> ty.Iterator[str]:
    """Get applications id for given RecentInfo @item"""
    # some duplicates are expected but we can live with this
    for app in item.get_applications():
        # get app_id from application info
        instr = item.get_application_info(app)[0]
        app = app.lower()
        yield app
        # get first word as app id
        if (aid := instr.split(None, 1)[0]) != app:
            yield aid


def _get_items(
    for_app_names: tuple[str, ...] | None = None,
) -> ty.Iterator[tuple[int, str]]:
    """Get recent items `for_app_names`.

    for_app_names: set of candidate app names, or None.
    Return iterable: tuple (modification time, file path)
    """
    max_days = __kupfer_settings__["max_days"]
    check_doc_exist = __kupfer_settings__["check_doc_exist"]
    for file_path, modified, apps in _get(max_days, check_doc_exist):
        if for_app_names:
            if not any(a in for_app_names for a in apps):
                continue

            ext = path.splitext(file_path)[1].lower()
            # check is any of app_id is in separate_apps dict, then check
            # extension of file - if is on list and matched application
            # is not @for_app_names list - skip file.
            # this allow to filter files for applications by file extension
            if any(
                sort_table.get(ext) not in for_app_names
                for app_id, sort_table in SEPARATE_APPS.items()
                if app_id in for_app_names
            ):
                continue

        yield (modified, file_path)


def _get_items_sorted(
    for_app_names: tuple[str, ...] | None = None,
) -> ty.Iterator[FileLeaf]:
    """Get recent documents as iterable FileLeaf for `for_app_names` sorted
    sorted by modified date desc."""
    items = sorted(_get_items(for_app_names), reverse=True)
    return (FileLeaf(item[1]) for item in items)


@functools.lru_cache(maxsize=10)
def _has_items_for_application(app_names: tuple[str, ...]) -> bool:
    """Check is there any recent documents for `app_names`."""
    # Cache doesn't need to be large to serve main purpose:
    # there will be many identical queries in a row
    for _item in _get_items(app_names):
        return True

    return False


def _app_names(leaf: AppLeaf) -> tuple[str, ...]:
    """Return a tuple of names for appleaf"""
    # in most cases, there are only 2-3 items, so there is not need to
    # built set
    svc = launch.get_applications_matcher_service()

    leaf_id = leaf.get_id()
    ids = [leaf_id]

    if (exe := leaf.object.get_executable()) != leaf_id:
        ids.append(exe)

    if app_name := svc.application_name(leaf_id):
        if (app_name := app_name.lower()) != leaf_id:
            ids.append(app_name)

    ids.extend(v for k, v in ALIASES.items() if k in ids)
    # return tuple as wee need hashable object for caching
    return tuple(ids)


class RecentsSource(Source):
    def __init__(self, name=None):
        super().__init__(name or _("Recent Items"))

    def initialize(self):
        """Set up change callback"""
        manager = Gtk.RecentManager.get_default()
        weaklib.gobject_connect_weakly(manager, "changed", self._recent_changed)

    def _recent_changed(self, _rmgr: Gtk.RecentManager) -> None:
        # when using typeguard lru_cache is wrapped
        try:
            _get.cache_clear()
        except AttributeError:
            _get.__wrapped__.cache_clear()  # type:ignore

        self.mark_for_update()

    def get_items(self):
        return _get_items_sorted()

    def get_description(self):
        return _("Recently used documents")

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf
        yield UrlLeaf


class ApplicationRecentsSource(RecentsSource):
    def __init__(self, application):
        # TRANS: Recent Documents for application %s
        name = _("%s Documents") % str(application)
        super().__init__(name)
        self.application = application

    def repr_key(self):
        return self.application.repr_key()

    def get_items(self):
        app_names = _app_names(self.application)
        self.output_debug("Items for", app_names)
        return _get_items_sorted(app_names)

    def get_gicon(self):
        return icons.ComposedIcon(
            self.get_icon_name(), self.application.get_icon()
        )

    def get_description(self):
        return _("Recently used documents for %s") % str(self.application)

    @classmethod
    def decorates_type(cls):
        return AppLeaf

    @classmethod
    def decorate_item(cls, leaf: AppLeaf) -> ApplicationRecentsSource | None:
        if IgnoredApps.contains(leaf):
            return None

        app_names = _app_names(leaf)
        if _has_items_for_application(app_names):
            return cls(leaf)

        return None


class PlacesSource(Source):
    """Source for items from gtk bookmarks/"""

    source_scan_interval: int = 3600

    def __init__(self):
        super().__init__(_("Places"))
        self.places_file = None
        self._version = 2

    def initialize(self):
        self.places_file = path.join(
            base.xdg_config_home, "gtk-3.0", "bookmarks"
        )

    def get_items(self):
        """
        gtk-bookmarks: each line has url and optional title
        file:///path/to/that.end [title]
        """
        assert self.places_file
        if Path(self.places_file).exists():
            return self._get_places(self.places_file)

        return ()

    def _get_places(self, fileloc):
        with open(fileloc, encoding="UTF-8") as fin:
            for line in fin:
                line = line.strip()
                if not line:
                    continue

                uri, *rest = line.split(None, 1)
                gfile = Gio.File.new_for_uri(uri)
                if rest:
                    title = rest[0]
                else:
                    disp = gfile.get_parse_name()
                    title = path.basename(disp)

                if locpath := gfile.get_path():
                    yield FileLeaf(locpath, title)
                else:
                    yield UrlLeaf(gfile.get_uri(), title)

    def get_description(self):
        return _("Bookmarked folders")

    def get_icon_name(self):
        return "system-file-manager"

    def provides(self):
        yield FileLeaf
        yield UrlLeaf


class IgnoredApps(Source):
    # This Source is invisibile and has no content
    # It exists just to store (through the config mechanism) the list of apps
    # we ignore for recent documents content decoration
    instance: IgnoredApps = None  # type:ignore
    source_scan_interval: int = 3600

    def __init__(self):
        super().__init__(_("Toggle Recent Documents"))
        self._version = 2
        self.apps: set[str] = set()

    def config_save(self):
        return self.apps

    def config_save_name(self):
        return __name__

    def config_restore(self, state):
        self.apps = state

    def initialize(self):
        IgnoredApps.instance = self

    def finalize(self):
        del IgnoredApps.instance

    def get_items(self):
        return []

    def provides(self):
        return ()

    @classmethod
    def add(cls, app_leaf):
        assert cls.instance
        cls.instance.apps.add(app_leaf.get_id())
        # FIXME: Semi-hack to refresh the content
        cls.instance.mark_for_update()

    @classmethod
    def remove(cls, app_leaf):
        assert cls.instance
        cls.instance.apps.discard(app_leaf.get_id())
        cls.instance.mark_for_update()

    @classmethod
    def contains(cls, app_leaf):
        assert cls.instance
        return app_leaf.get_id() in cls.instance.apps

    def get_leaf_repr(self):
        return InvisibleSourceLeaf(self)


class Toggle(Action):
    rank_adjust = -5

    def __init__(self):
        super().__init__(_("Toggle Recent Documents"))

    def item_types(self):
        yield AppLeaf

    def valid_for_item(self, leaf):
        if IgnoredApps.contains(leaf):
            return True

        app_names = _app_names(leaf)
        return _has_items_for_application(app_names)

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        if IgnoredApps.contains(leaf):
            IgnoredApps.remove(leaf)
        else:
            IgnoredApps.add(leaf)
        # Neat trick: We return the leaf, and that updates the decoration
        # pylint: disable=protected-access
        leaf._content_source = None
        return leaf

    def get_description(self):
        return _(
            "Enable/disable listing recent documents in "
            "content for this application"
        )


class InvisibleSourceLeaf(SourceLeaf):
    """Hack to hide this source"""

    def is_valid(self):
        return False
