__kupfer_name__ = _("Custom Theme")
__description__ = ""
__version__ = "2017.1"
__author__ = "Chaitanya Lakkundi"

from gi.repository import Gtk

from kupfer import plugin_support, pretty, config
from shutil import copyfile

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "css_file",
        "label": "Select the theme",
        "type": str,
        "value": "Light",
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

def use_theme(theme):
    if theme != "Custom":
        new_css_file = config.get_data_file('style.css.'+theme.lower())
        default_css_file = config.get_data_file('style.css')

        copyfile(new_css_file, default_css_file)
    else:
        pass
        #colorpicker
    pretty.print_debug(__name__, "updating setting to", theme+" theme")
