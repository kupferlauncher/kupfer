from contextlib import suppress

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
with suppress(ValueError):
    gi.require_version("Wnck", "3.0")

with suppress(ValueError):
    gi.require_version("AppIndicator3", "0.1")
