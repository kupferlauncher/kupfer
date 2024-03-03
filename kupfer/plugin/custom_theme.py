__kupfer_name__ = _("Custom Theme")
__description__ = "Apply any custom theme"
__version__ = "2017.5"
__author__ = "Chaitanya S Lakkundi"

from gi.repository import Gtk, Gdk
from gi.repository import Gio, GLib

from kupfer import plugin_support, pretty, config

from glob import glob
from os.path import basename

def get_alternative_themes():
    base_dir = config.get_data_home()
    css_files = glob(base_dir+"/*.css")
    themes = [basename(filename[:-4]) for filename in css_files]
    if themes:
        return tuple(themes)
    else:
        return "None",

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "theme",
        "label": "Select the theme",
        "type": str,
        "value": get_alternative_themes()[0],
        "alternatives": get_alternative_themes()
    },
)

def initialize_plugin(name):
    try:
        use_theme(__kupfer_settings__['theme'])
    except config.ResourceLookupError as e:
        pretty.print_debug(__name__, e)

    __kupfer_settings__.connect_settings_changed_cb(on_change_theme)

def on_change_theme(sender, key, value):
    try:
        use_theme(value)
    except config.ResourceLookupError as e:
        pretty.print_debug(__name__, e)
        use_theme("light")

def finalize_plugin(name):
    use_theme('light')

def load_style_css(css_file):
    pretty.print_debug(__name__,'loading style from css file: ', css_file)
    css_file = Gio.File.new_for_path(css_file)
    style_provider = Gtk.CssProvider()
    # Gtk.StyleContext.remove_provider_for_screen(
    #         Gdk.Screen.get_default(),
    #         style_provider,
    #     )
    try:
        style_provider.load_from_file(css_file)
    except GLib.Error:
        pretty.print_debug(__name__, 'Error parsing the css file')
        return None

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

def use_theme(theme):
    try:
        css_file = config.get_data_file(theme+".css")
        load_style_css(css_file)
    except:
        pretty.print_debug(__name__, "Theme "+theme+" could not be applied")
