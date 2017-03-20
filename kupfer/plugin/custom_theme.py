__kupfer_name__ = _("Custom Theme")
__description__ = ""
__version__ = "2017.1"
__author__ = "Chaitanya S Lakkundi"

from gi.repository import Gtk, Gdk
from gi.repository import Gio, GLib

from kupfer import plugin_support, pretty, config
from shutil import copyfile

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "css_file",
        "label": "Select the theme",
        "type": str,
        "value": "",
        "alternatives":(
            "Light",
            "Dark",
            "Custom",
            )
    },
)

def initialize_plugin(name):
    use_theme(__kupfer_settings__['css_file'])
    __kupfer_settings__.connect_settings_changed_cb(on_change_theme)

def finalize_plugin(name):
    use_theme(None)

def on_change_theme(sender, key, value):
    use_theme(value)

def load_style_css(css_file):
        pretty.print_debug(__name__,'loading style from css file: ', css_file)
        css_file = Gio.File.new_for_path(css_file)
        style_provider = Gtk.CssProvider()
        Gtk.StyleContext.remove_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
            )
        try:
            style_provider.load_from_file(css_file)
        except GLib.Error:
            print('Error parsing the css file')
            return None
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

#FIXME: Not able to switch back to Light theme in the same running instance
def use_theme(theme):
    if not theme:
        pretty.print_debug(__name__, "Default theme selected")
        css_file = config.get_data_file('style.css')
        load_style_css(css_file)

    elif theme == "Custom":
        pass
    else:
        css_file = config.get_data_file('style.css.'+theme.lower())
        load_style_css(css_file)
