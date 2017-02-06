# TRANS: Multihead refers to support for multiple computer displays
# TRANS: In this case, it only concerns the special configuration
# TRANS: with multiple X "screens"
__kupfer_name__ = _("Multihead Support")
__kupfer_sources__ = ()
__description__ = ("Will run the keyboard shortcut relay service on additional"
                   " X screens if needed.")
__version__ = ""
__author__ = ""

import os

from gi.repository import Gdk

from kupfer import pretty
from kupfer import utils

child_pids = []

def initialize_plugin(name):
    global pid
    ## check for multihead
    display = Gdk.Display.get_default()
    screen = display.get_default_screen()
    if display.get_n_screens() > 1:
        pretty.print_info(__name__, "Starting Multi X screen support")
        for idx in range(display.get_n_screens()):
            if idx != screen.get_number():
                pretty.print_info(__name__, "Launching keyrelay for screen", idx)
                screen_x = display.get_screen(idx)
                # run helper without respawning it
                pid = utils.start_plugin_helper("kupfer.keyrelay",
                        False, screen_x.make_display_name())
                child_pids.append(pid)


def finalize_plugin(name):
    for pid in child_pids:
        os.kill(pid, 1)
    child_pids[:] = []
