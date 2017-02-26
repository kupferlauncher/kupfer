from gi.repository import Gtk

from kupfer.objects import Source, RunnableLeaf
from kupfer.obj.apps import AppLeafContentMixin
from kupfer import pretty
from kupfer import kupferui
from kupfer.version import DESKTOP_ID

__kupfer_sources__ = ("KupferSource", )
__kupfer_actions__ = ()
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__all__ = __kupfer_sources__ + __kupfer_actions__

def _is_debug():
    # Return True if Kupfer is in debug mode
    return pretty.debug

class DebugRestart (RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, None, _("Restart Kupfer"))

    @classmethod
    def _exec_new_kupfer(cls, executable, argv):
        import os
        os.execvp(executable, [executable] + argv)

    def run(self):
        import atexit
        import sys
        Gtk.main_quit()
        atexit.register(self._exec_new_kupfer, sys.executable, sys.argv)

    def get_description(self):
        return str(self)

    def get_icon_name(self):
        return "view-refresh"

class Quit (RunnableLeaf):
    qf_id = "quit"
    def __init__(self, name=None):
        if not name: name = _("Quit")
        super(Quit, self).__init__(name=name)
    def run(self):
        Gtk.main_quit()
    def get_description(self):
        return _("Quit Kupfer")
    def get_icon_name(self):
        return "application-exit"

class About (RunnableLeaf):
    def __init__(self, name=None):
        if not name: name = _("About Kupfer")
        super(About, self).__init__(name=name)
    def wants_context(self):
        return True
    def run(self, ctx):
        kupferui.show_about_dialog(ctx.environment)
    def get_description(self):
        return _("Show information about Kupfer authors and license")
    def get_icon_name(self):
        return "help-about"

class Help (RunnableLeaf):
    def __init__(self, name=None):
        if not name: name = _("Kupfer Help")
        super(Help, self).__init__(name=name)
    def wants_context(self):
        return True
    def run(self, ctx):
        kupferui.show_help(ctx.environment)
    def get_description(self):
        return _("Get help with Kupfer")
    def get_icon_name(self):
        return "help-contents"

class Preferences (RunnableLeaf):
    def __init__(self, name=None):
        if not name: name = _("Kupfer Preferences")
        super(Preferences, self).__init__(name=name)
    def wants_context(self):
        return True
    def run(self, ctx):
        kupferui.show_preferences(ctx.environment)
    def get_description(self):
        return _("Show preferences window for Kupfer")
    def get_icon_name(self):
        return "preferences-desktop"

class KupferSource (AppLeafContentMixin, Source):
    appleaf_content_id = DESKTOP_ID
    def __init__(self, name=_("Kupfer")):
        Source.__init__(self, name)
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
