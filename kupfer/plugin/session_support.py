'''
Common objects for session_* plugins.
'''

from kupfer.objects import Source, RunnableLeaf
from kupfer import utils, pretty

__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


def launch_argv_with_fallbacks(commands, print_error=True):
    """Try the sequence of @commands with utils.spawn_async,
    and return with the first successful command.
    return False if no command is successful and log an error
    """
    for argv in commands:
        ret = utils.spawn_async(argv)
        if ret: return ret
    pretty.print_error(__name__, "Unable to run command(s)", commands)
    return False

class CommandLeaf (RunnableLeaf):
    """The represented object of the CommandLeaf is a list of commandlines"""
    def run(self):
        launch_argv_with_fallbacks(self.object)

class Logout (CommandLeaf):
    """Log out from desktop"""
    def __init__(self, commands, name=None):
        if not name: name = _("Log Out...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("Log out or change user")
    def get_icon_name(self):
        return "system-log-out"

class Shutdown (CommandLeaf):
    """Shutdown computer or reboot"""
    def __init__(self, commands, name=None):
        if not name: name = _("Shut Down...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("Shut down, restart or suspend computer")
    def get_icon_name(self):
        return "system-shutdown"

class LockScreen (CommandLeaf):
    """Lock screen"""
    def __init__(self, commands, name=None):
        if not name: name = _("Lock Screen")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("Enable screensaver and lock")
    def get_icon_name(self):
        return "system-lock-screen"

class CommonSource (Source):
    def __init__(self, name):
        super(CommonSource, self).__init__(name)
    def is_dynamic(self):
        return True
    def get_icon_name(self):
        return "system-shutdown"
    def provides(self):
        yield RunnableLeaf
