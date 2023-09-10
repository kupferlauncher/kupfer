import atexit
import os
import sys
import typing as ty

from gi.repository import Gtk

from kupfer.obj import RunnableLeaf, Source
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.support import pretty
from kupfer.ui import about, kupferhelp, preferences
from kupfer.version import DESKTOP_ID

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_sources__ = ("KupferSource",)
__kupfer_actions__ = ()
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__all__ = __kupfer_sources__ + __kupfer_actions__


def _is_debug():
    # Return True if Kupfer is in debug mode
    return pretty.DEBUG


class DebugRestart(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, None, _("Restart Kupfer"))

    @classmethod
    def _exec_new_kupfer(cls, executable, argv):
        os.execvp(executable, [executable] + argv)

    def run(self, ctx=None):
        Gtk.main_quit()
        atexit.register(self._exec_new_kupfer, sys.executable, sys.argv)

    def get_description(self):
        return str(self)

    def get_icon_name(self):
        return "view-refresh"


class Quit(RunnableLeaf):
    qf_id = "quit"

    def __init__(self, name=None):
        super().__init__(name=name or _("Quit"))

    def run(self, ctx=None):
        Gtk.main_quit()

    def get_description(self):
        return _("Quit Kupfer")

    def get_icon_name(self):
        return "application-exit"


class About(RunnableLeaf):
    def __init__(self, name=None):
        if not name:
            name = _("About Kupfer")
        super().__init__(name=name)

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx
        about.show_about_dialog(ctx.environment)

    def get_description(self):
        return _("Show information about Kupfer authors and license")

    def get_icon_name(self):
        return "help-about"


class Help(RunnableLeaf):
    def __init__(self, name=None):
        super().__init__(name=name or _("Kupfer Help"))

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx
        kupferhelp.show_help(ctx.environment)

    def get_description(self):
        return _("Get help with Kupfer")

    def get_icon_name(self):
        return "help-contents"


class Preferences(RunnableLeaf):
    def __init__(self, name=None):
        super().__init__(name=name or _("Kupfer Preferences"))

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx
        preferences.show_preferences(ctx.environment)

    def get_description(self):
        return _("Show preferences window for Kupfer")

    def get_icon_name(self):
        return "preferences-desktop"


class KupferSource(AppLeafContentMixin, Source):
    appleaf_content_id = DESKTOP_ID

    def __init__(self, name=None):
        Source.__init__(self, name or _("Kupfer"))

    def is_dynamic(self):
        return True

    def get_items(self):
        yield Preferences()
        yield Help()
        yield About()
        yield Quit()
        yield DebugRestart()

    def get_description(self):
        return None

    def get_icon_name(self):
        return "search"

    def provides(self):
        yield RunnableLeaf
