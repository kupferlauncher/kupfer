__kupfer_name__ = _("Darkstyle")
__kupfer_sources__ = ()
__description__ = _("Use a dark color theme in Kupfer")
__version__ = ""
__author__ = ""

import gtk

def initialize_plugin(name):
	settings = gtk.settings_get_default()
	settings.set_property("gtk-color-scheme", DARK_COLORS)

def finalize_plugin(name):
	settings = gtk.settings_get_default()
	settings.set_property("gtk-color-scheme", "")

## Based upon darklooks but with Gray, not blue text
DARK_COLORS = ("fg_color:#E6E6E6\n"
               "bg_color:#555753\n"
               "base_color:#2E3436\n"
               "text_color:#D3D7CF\n"
               "selected_bg_color:#3F403D\n"
               "selected_fg_color:#CCCCCC\n"
               "tooltip_bg_color:#EDDE5C\n"
               "tooltip_fg_color:#000000")
