__kupfer_name__ = _("Applications")
__kupfer_sources__ = ("AppSource",)
__kupfer_actions__ = (
    "OpenWith",
    "SetDefaultApplication",
    "ResetAssociations",
)
__description__ = _("All applications and preferences")
__version__ = "2017.3"
__author__ = ""

import typing as ty

from gi.repository import Gio

from kupfer import config, plugin_support
from kupfer.obj import Action, AppLeaf, FileLeaf, Source
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.support import weaklib

if ty.TYPE_CHECKING:
    _ = str

_ALTERNATIVES = (
    "",
    "Cinnamon",
    "EDE",
    "GNOME",
    "KDE",
    "LXDE",
    "LXQt",
    "MATE",
    "Pantheon",
    "ROX",
    "Razor",
    "TDE",
    "Unity",
    "XFCE",
)

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "desktop_type",
        "label": _("Applications for Desktop Environment"),
        "type": str,
        "value": "",
        "alternatives": _ALTERNATIVES,
    },
    {
        "key": "desktop_filter",
        "label": _("Use Desktop Filter"),
        "type": bool,
        "value": True,
    },
)

# Gio.AppInfo / Desktop Item nodisplay vs hidden:
# NoDisplay: Don't show this in program menus
# Hidden: Disable/never use at all

WHITELIST_IDS: ty.Final = (
    # we think that these are useful to show
    "eog.desktop",
    "evince.desktop",
    "gnome-about.desktop",
    "gstreamer-properties.desktop",
    "notification-properties.desktop",
    "shotwell-viewer.desktop",
)
BLACKLIST_IDS: ty.Final = ("nautilus-home.desktop",)


def _should_show(
    app_info: Gio.AppInfo, desktop_type: str, use_filter: bool
) -> bool:
    if app_info.get_nodisplay():
        return False

    if not use_filter:
        return True

    if desktop_type == "":
        return app_info.should_show()  # type: ignore

    return app_info.get_show_in(desktop_type)  # type:ignore


class AppSource(Source, FilesystemWatchMixin):
    """
    Applications source

    This Source contains all user-visible applications (as given by
    the desktop files)
    """

    def __init__(self, name=None):
        super().__init__(name or _("Applications"))
        self.monitor_token = None

    def initialize(self):
        application_dirs = config.get_data_dirs("", "applications")
        self.monitor_token = self.monitor_directories(*application_dirs)
        weaklib.gobject_connect_weakly(
            __kupfer_settings__,
            "plugin-setting-changed",
            self._on_setting_change,
        )

    def _on_setting_change(self, *_args):
        self.mark_for_update()

    def get_items(self):
        use_filter = __kupfer_settings__["desktop_filter"]
        desktop_type = __kupfer_settings__["desktop_type"]

        # Add this to the default
        for item in Gio.app_info_get_all():
            id_ = item.get_id()
            if id_ in WHITELIST_IDS or (
                _should_show(item, desktop_type, use_filter)
                and id_ not in BLACKLIST_IDS
            ):
                yield AppLeaf(item)

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return _("All applications and preferences")

    def get_icon_name(self):
        return "applications-office"

    def provides(self):
        yield AppLeaf


class OpenWith(Action):
    action_accelerator = "w"

    def __init__(self):
        super().__init__(_("Open With..."))

    def _activate(self, app_leaf, paths, ctx):
        app_leaf.launch(paths=paths, ctx=ctx)

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        assert iobj
        self.activate_multiple((leaf,), (iobj,), ctx)

    def activate_multiple(self, objects, iobjects, ctx):
        # for each application, launch all the files
        for iobj_app in iobjects:
            self._activate(iobj_app, [L.object for L in objects], ctx)

    def item_types(self):
        yield FileLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield AppLeaf

    def object_source(self, for_item=None):
        return AppsAll()

    def object_source_and_catalog(self, for_item):
        return True

    def valid_object(self, iobj, for_item):
        return iobj.object.supports_files() or iobj.object.supports_uris()

    def get_description(self):
        return _("Open with any application")


class SetDefaultApplication(Action):
    def __init__(self):
        super().__init__(_("Set Default Application..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        desktop_item = iobj.object
        desktop_item.set_as_default_for_type(leaf.get_content_type())

    def item_types(self):
        yield FileLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield AppLeaf

    def object_source(self, for_item=None):
        return AppsAll()

    def object_source_and_catalog(self, for_item):
        return True

    def valid_object(self, iobj, for_item):
        return iobj.object.supports_files() or iobj.object.supports_uris()

    def get_description(self):
        return _("Set default application to open this file type")


class AppsAll(Source):
    def __init__(self):
        super().__init__(_("Applications"))

    def get_items(self):
        use_filter = __kupfer_settings__["desktop_filter"]
        desktop_type = __kupfer_settings__["desktop_type"]

        # Get all apps; this includes those only configured for
        # opening files with.
        for item in Gio.AppInfo.get_all():
            if _should_show(item, desktop_type, use_filter):
                continue

            if not item.supports_uris() and not item.supports_files():
                continue

            yield AppLeaf(item)

    def should_sort_lexically(self):
        return False

    def get_description(self):
        return None

    def get_icon_name(self):
        return "applications-office"

    def provides(self):
        yield AppLeaf


class ResetAssociations(Action):
    rank_adjust = -10

    def __init__(self):
        super().__init__(_("Reset Associations"))

    def activate(self, leaf, iobj=None, ctx=None):
        content_type = leaf.get_content_type()
        Gio.AppInfo.reset_type_associations(content_type)

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Reset program associations for files of this type.")
