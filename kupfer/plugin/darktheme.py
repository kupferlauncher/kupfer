__kupfer_name__ = _("Prefer Dark Theme")
__description__ = ""
__version__ = "2017.1"
__author__ = ""

from gi.repository import Gtk

from kupfer import plugin_support, pretty

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "prefer_dark",
        "label": _("Prefer Dark Theme"),
        "type": bool,
        "value": True,
    },
)

def initialize_plugin(name):
    use_theme(__kupfer_settings__['prefer_dark'])
    __kupfer_settings__.connect_settings_changed_cb(on_change_theme)

def finalize_plugin(name):
    use_theme(None)

def on_change_theme(sender, key, value):
    use_theme(value)

PREFER_DARK = "gtk-application-prefer-dark-theme"

def use_theme(enabled):
    pretty.print_debug(__name__, "updating setting to", enabled)
    s = Gtk.Settings.get_default()
    if enabled is None:
        s.reset_property(PREFER_DARK)
    else:
        s.set_property(PREFER_DARK, enabled)
