__kupfer_name__ = _("Custom Theme")
__kupfer_sources__ = ()
__description__ = _("Use a custom color theme")
__version__ = ""
__author__ = ""

import os
import gtk

from kupfer import config
from kupfer import plugin_support

"""
Kupfer's UI can be themed by using the normal GtkRc style language
Theming can change colors and some pre-defined parameters, but
not the layout.

See also Documentation/GTKTheming.rst
      or http://kaizer.se/wiki/kupfer/GTKTheming.html

For general information about GTK+ styles,
please see http://live.gnome.org/GnomeArt/Tutorials/GtkThemes

"""

SQUARE_STYLE = """
style "square"
{
    MatchView :: corner-radius = 0
    MatchView :: opacity = 100
    Search :: list-opacity = 100
    KupferWindow :: corner-radius = 0
    KupferWindow :: opacity = 100
    KupferWindow :: decorated = 0
    KupferWindow :: border-width = 4

}

## The main window is kupfer
widget "kupfer" style "square"
widget "kupfer.*" style "square"

## The result list is kupfer-list
widget "kupfer-list.*" style "square"
"""

DARK_STYLE = """
style "dark"
{
    ## bg: background color
    bg[NORMAL] = "#333"
    bg[SELECTED] = "#000"
    bg[ACTIVE] = "#222"
    bg[PRELIGHT] = "#222"
    bg[INSENSITIVE] = "#333"

    ## fg: foreground text color
    fg[NORMAL] = "#DDD"
    fg[SELECTED] = "#EEE"
    fg[ACTIVE] = "#EEE"
    fg[PRELIGHT] = "#EEE"
    fg[INSENSITIVE] = "#DDD"

    ## text: text color in input widget and treeview
    text[NORMAL] = "#EEE"
    text[SELECTED] = "#EEE"
    text[ACTIVE] = "#EEE"

    ## base: background color in input widget and treeview
    base[NORMAL] = "#777"
    base[SELECTED] = "#100"
    base[ACTIVE] = "#112"

    ## These are UI Widget style properties with their approximate
    ## default values. These can all be overidden in the theme.
    ## MatchView :: corner-radius = 15
    MatchView :: opacity = 90
    ## Search :: list-opacity = 93
    ## KupferWindow :: corner-radius = 15
    KupferWindow :: opacity = 90
    ## KupferWindow :: decorated = 0
    ## KupferWindow :: border-width = 8
}

## The main window is kupfer
widget "kupfer" style "dark"
widget "kupfer.*" style "dark"

## The result list is kupfer-list
widget "kupfer-list.*" style "dark"

## The menu button is *.kupfer-menu-button
## widget "*.kupfer-menu-button" style "dark"
## The description text is *.kupfer-description
## widget "*.kupfer-description" style "dark"
## The context menu is GtkWindow.kupfer-menu
## widget "*.kupfer-menu" style "dark"
"""


all_styles = {
    'default': None,
    'square': SQUARE_STYLE,
    'dark': DARK_STYLE,
}

__kupfer_settings__ = plugin_support.PluginSettings(
        {
            "key": "theme",
            "label": _("Theme:"),
            "type": str,
            "value": 'default',
            "alternatives": list(all_styles.keys()),
        },
    )

def cache_filename():
    return os.path.join(config.get_cache_home(), __name__)

def re_read_theme():
    ## force re-read theme
    ## FIXME: re-read on all screens
    settings = gtk.settings_get_default()
    gtk.rc_reparse_all_for_settings(settings, True)

def initialize_plugin(name):
    """
    Theme changes are only reversible if we add
    and remove gtkrc files.
    """
    use_theme(all_styles.get(__kupfer_settings__['theme']))
    __kupfer_settings__.connect_settings_changed_cb(on_change_theme)

def on_change_theme(sender, key, value):
    if key == 'theme':
        use_theme(all_styles.get(__kupfer_settings__[key]))

def use_theme(style_str):
    """
    Use the GTK+ style in @style_str,
    or unset if it is None
    """
    filename = cache_filename()
    if style_str is None:
        filename = cache_filename()
        gtk.rc_set_default_files([f for f in gtk.rc_get_default_files()
                                  if f != filename])
    else:
        with open(filename, "wb") as rcfile:
            rcfile.write(style_str)
        gtk.rc_add_default_file(filename)
    re_read_theme()

def finalize_plugin(name):
    use_theme(None)
    re_read_theme()
    ## remove cache file
    filename = cache_filename()
    assert ("kupfer" in filename)
    try:
        os.unlink(filename)
    except OSError:
        pass
