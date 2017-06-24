__kupfer_name__ = _("KDE5 Session Management")
__kupfer_sources__ = ("KDEItemsSource", )
__description__ = _("Special items and actions for KDE environment")
__version__ = "2017-06-22"
__author__ = "Thorsten Kohlhepp"

import subprocess
from kupfer.objects import Source, RunnableLeaf
from kupfer import utils, pretty

def launch_argv_with_fallbacks(commands, print_error=True):
    """Try the sequence of @commands with utils.spawn_async,
    and return with the first successful command.
    return False if no command is successful and log an error
    """
    for argv in commands:
        pretty.print_error(__name__, 'command: ', argv)
        subprocess.Popen(argv, shell=True, stdout=subprocess.PIPE)
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

class Restart (CommandLeaf):
    """Shutdown computer or reboot"""
    def __init__(self, commands, name=None):
        if not name: name = _("Restart...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("restart computer")
    def get_icon_name(self):
        return "system-reboot"

class LockScreen (CommandLeaf):
    """Shutdown computer or reboot"""
    def __init__(self, commands, name=None):
        if not name: name = _("Lock Screen...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("Locks the screen")
    def get_icon_name(self):
        return "system-lock-screen"

class Suspend (CommandLeaf):
    """Shutdown computer or reboot"""
    def __init__(self, commands, name=None):
        if not name: name = _("Suspend...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("suspend computer")
    def get_icon_name(self):
        return "system-suspend"

class SaveSession (CommandLeaf):
    """"""
    def __init__(self, commands, name=None):
        if not name: name = _("Save session...")
        CommandLeaf.__init__(self, commands, name)
    def get_description(self):
        return _("save session")
    def get_icon_name(self):
        return "document-save"


class CommonSource (Source):
    def __init__(self, name):
        super(CommonSource, self).__init__(name)
    def is_dynamic(self):
        return True
    def get_icon_name(self):
        return "system-shutdown"
    def provides(self):
        yield RunnableLeaf

# sequences of argument lists
LOGOUT_CMD = (["qdbus org.kde.ksmserver /KSMServer logout 0 0 0"])
SHUTDOWN_CMD = (["qdbus org.kde.ksmserver /KSMServer logout 0 2 0"])
RESTART_CMD = (["qdbus org.kde.ksmserver /KSMServer logout 0 1 0"])
LOCK_CMD = (["qdbus org.kde.ksmserver /ScreenSaver Lock"])
SUSPEND_CMD = (["qdbus org.kde.Solid.PowerManagement /org/freedesktop/PowerManagement Suspend"])
SAVE_SESSION_CMD = (["qdbus org.kde.ksmserver /KSMServer saveCurrentSession"])

class KDEItemsSource (CommonSource):
    def __init__(self):
        CommonSource.__init__(self, _("KDE5 Session Management"))
    def get_items(self):
        return (
            Logout(LOGOUT_CMD),
            Shutdown(SHUTDOWN_CMD),
            Suspend(SUSPEND_CMD),
            Restart(RESTART_CMD),
            LockScreen(LOCK_CMD),
            SaveSession(SAVE_SESSION_CMD),
        )


