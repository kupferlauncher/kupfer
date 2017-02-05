__kupfer_name__ = _("GNOME Terminal Profiles")
__kupfer_sources__ = ("SessionsSource", )
__description__ = _("Launch GNOME Terminal profiles")
__version__ = ""
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import os

import gconf
import glib

from kupfer.objects import Leaf, Action
from kupfer.obj.apps import ApplicationSource
from kupfer import utils, icons


GCONF_KEY = "/apps/gnome-terminal/profiles"


class Terminal(Leaf):
    """ Leaf represent profile saved in GNOME Terminal"""

    def __init__(self, name):
        Leaf.__init__(self, name, name)

    def get_actions(self):
        yield OpenSession()

    def get_icon_name(self):
        return "terminal"


class OpenSession(Action):
    """ Opens GNOME Terminal profile """
    def __init__(self):
        Action.__init__(self, _("Open"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        utils.spawn_async(["gnome-terminal",
                   "--profile=%s" % leaf.object,
                   "--display=%s" % ctx.environment.get_display()],
                  in_dir=os.path.expanduser("~"))

    def get_gicon(self):
        return icons.ComposedIcon("gtk-execute", "terminal")


class SessionsSource(ApplicationSource):
    """ Yield GNOME Terminal profiles """
    appleaf_content_id = 'gnome-terminal'

    def __init__(self):
        ApplicationSource.__init__(self, name=_("GNOME Terminal Profiles"))

    def get_items(self):
        gc = gconf.client_get_default()
        try:
            if not gc.dir_exists(GCONF_KEY):
                return

            for entry in gc.all_dirs(GCONF_KEY):
                yield Terminal(gc.get_string("%s/visible_name" % entry))
        except glib.GError as err:
            self.output_error(err)

    def should_sort_lexically(self):
        return True

    def get_icon_name(self):
        return "terminal"

    def provides(self):
        yield Terminal

