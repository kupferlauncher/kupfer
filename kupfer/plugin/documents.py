__kupfer_name__ = _("Documents")
__kupfer_sources__ = ("RecentsSource", "PlacesSource", "IgnoredApps", )
__kupfer_actions__ = ("Toggle", )
__kupfer_contents__ = ("ApplicationRecentsSource", )
__description__ = _("Recently used documents and bookmarked folders")
__version__ = "2017.3"
__author__ = ""

import operator
import functools
from os import path
import xdg.BaseDirectory as base

from gi.repository import Gio, Gtk

from kupfer.objects import Action, Source
from kupfer.objects import SourceLeaf, AppLeaf, FileLeaf, UrlLeaf
from kupfer import icons
from kupfer import launch
from kupfer import plugin_support
from kupfer.weaklib import gobject_connect_weakly

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "max_days",
        "label": _("Max recent document days"),
        "type": int,
        "value": 28,
    },
)

ALIASES = {
    'libreoffice': 'soffice',
}

# Libreoffice doesn't separate them out, so we'll hack that in manually
SEPARATE_APPS = {
    'libreoffice': {
        '.doc': 'libreoffice-writer',
        '.docx': 'libreoffice-writer',
        '.odt': 'libreoffice-writer',
        '.ods': 'libreoffice-calc',
        '.xlsx': 'libreoffice-calc',
        '.csv': 'libreoffice-calc',
        '.odp': 'libreoffice-impress',
        '.ppt': 'libreoffice-impress',
        '.pptx': 'libreoffice-impress',
        '.odg': 'libreoffice-draw',
        '.odf': 'libreoffice-math',
        '.mml': 'libreoffice-math',
    }
}

def _file_path(uri):
    try:
        return Gio.File.new_for_uri(uri).get_path()
    except Exception:
        # FIXME: encoding errors in get_path raise generic Exception
        return None

class RecentsSource (Source):
    def __init__(self, name=None):
        if not name:
            name = _("Recent Items")
        super().__init__(name)

    def initialize(self):
        """Set up change callback"""
        manager = Gtk.RecentManager.get_default()
        gobject_connect_weakly(manager, "changed", self._recent_changed)

    def _recent_changed(self, *args):
        # FIXME: We don't get single item updates, might this be
        # too many updates?
        self._get.cache_clear()
        self.mark_for_update()
    
    def get_items(self):
        max_days = __kupfer_settings__["max_days"]
        return self._get_items(max_days)

    @functools.lru_cache(maxsize=1)
    def _get(max_days):
        manager = Gtk.RecentManager.get_default()
        def first_word(s):
            return s.split(None, 1)[0]

        items = manager.get_items()
        item_leaves = []
        for item in items:
            day_age = item.get_age()
            if max_days >= 0 and day_age > max_days:
                continue
            if not item.exists():
                continue
            if item.get_private_hint():
                continue
            if not item.is_local():
                continue
            uri = item.get_uri()
            file_path = _file_path(uri)
            if not file_path:
                continue
            item_leaves.append((file_path, item.get_modified(), item))
        item_leaves.sort(key=operator.itemgetter(1), reverse=True)
        return item_leaves

    @staticmethod
    def _get_items(max_days, for_app_names=None):
        """
        for_app_names: set of candidate app names, or None.
        """
        def first_word(s):
            return s.split(None, 1)[0]

        for file_path, _modified, item in RecentsSource._get(max_days):
            if for_app_names:
                apps = item.get_applications()
                in_low_apps = any(A.lower() in for_app_names for A in apps)
                in_execs = any(first_word(item.get_application_info(A)[0])
                               in for_app_names for A in apps)
                if not in_low_apps and not in_execs:
                    continue

            if for_app_names:
                accept_item = True
                for app_id, sort_table in SEPARATE_APPS.items():
                    if app_id in for_app_names:
                        _, ext = path.splitext(file_path)
                        ext = ext.lower()
                        if ext in sort_table and sort_table[ext] not in for_app_names:
                            accept_item = False
                            break
                if not accept_item:
                    continue
            yield FileLeaf(file_path)

    def get_description(self):
        return _("Recently used documents")

    def get_icon_name(self):
        return "document-open-recent"
    def provides(self):
        yield FileLeaf
        yield UrlLeaf

class ApplicationRecentsSource (RecentsSource):
    def __init__(self, application):
        # TRANS: Recent Documents for application %s
        name = _("%s Documents") % str(application)
        super().__init__(name)
        self.application = application

    def repr_key(self):
        return self.application.repr_key()

    def get_items(self):
        app_names = self.app_names(self.application)
        max_days = __kupfer_settings__["max_days"]
        self.output_debug("Items for", app_names)
        items = self._get_items(max_days, app_names)
        return items

    # Cache doesn't need to be large to serve main purpose:
    # there will be many identical queries in a row
    @staticmethod
    @functools.lru_cache(maxsize=10)
    def has_items_for_application(names):
        max_days = __kupfer_settings__["max_days"]
        for item in RecentsSource._get_items(max_days, names):
            return True
        return False

    def get_gicon(self):
        return icons.ComposedIcon(self.get_icon_name(),
                self.application.get_icon())
    def get_description(self):
        return _("Recently used documents for %s") % str(self.application)

    @classmethod
    def decorates_type(cls):
        return AppLeaf

    @classmethod
    def decorate_item(cls, leaf):
        if IgnoredApps.contains(leaf):
            return None
        app_names = cls.app_names(leaf)
        if cls.has_items_for_application(app_names):
            return cls(leaf)
        return None

    @classmethod
    def app_names(cls, leaf):
        "Return a frozenset of names"
        svc = launch.GetApplicationsMatcherService()
        ids = [leaf.get_id()]
        app_name = svc.application_name(ids[0])
        if app_name is not None:
            ids.append(app_name.lower())
        ids.append(leaf.object.get_executable())
        for k, v in ALIASES.items():
            if k in ids:
                ids.append(v)
        return frozenset(ids)

class PlacesSource (Source):
    """
    Source for items from gtk bookmarks 
    """
    def __init__(self):
        super(PlacesSource, self).__init__(_("Places"))
        self.places_file = None
        self._version = 2

    def initialize(self):
        self.places_file = path.join(base.xdg_config_home, "gtk-3.0", "bookmarks")
    
    def get_items(self):
        """
        gtk-bookmarks: each line has url and optional title
        file:///path/to/that.end [title]
        """
        if not path.exists(self.places_file):
            return ()
        return self._get_places(self.places_file)

    def _get_places(self, fileloc):
        for line in open(fileloc):
            if not line.strip():
                continue
            items = line.split(None, 1)
            uri = items[0]
            gfile = Gio.File.new_for_uri(uri)
            if len(items) > 1:
                title = items[1].strip()
            else:
                disp = gfile.get_parse_name()
                title = path.basename(disp)
            locpath = gfile.get_path()
            if locpath:
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
    def __init__(self):
        super().__init__(_("Toggle Recent Documents"))
        # apps is a mapping: app id (str) -> empty dict
        self.apps = {}

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
        cls.instance.apps[app_leaf.get_id()] = {}
        # FIXME: Semi-hack to refresh the content
        cls.instance.mark_for_update()

    @classmethod
    def remove(cls, app_leaf):
        cls.instance.apps.pop(app_leaf.get_id(), None)
        cls.instance.mark_for_update()

    @classmethod
    def contains(cls, app_leaf):
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
        app_names = ApplicationRecentsSource.app_names(leaf)
        return ApplicationRecentsSource.has_items_for_application(app_names)

    def has_result(self):
        return True

    def activate(self, leaf):
        if IgnoredApps.contains(leaf):
            IgnoredApps.remove(leaf)
        else:
            IgnoredApps.add(leaf)
        # Neat trick: We return the leaf,
        # and that updates the decoration
        leaf._content_source = None
        return leaf

    def get_description(self):
        return _("Enable/disable listing recent documents in content for this application")

class InvisibleSourceLeaf (SourceLeaf):
    """Hack to hide this source"""
    def is_valid(self):
        return False
