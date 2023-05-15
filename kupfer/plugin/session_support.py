"""
Common objects for session_* plugins.
"""

import typing as ty

from kupfer import launch
from kupfer.obj import RunnableLeaf, Source
from kupfer.support import pretty
from kupfer.ui import uiutils

__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

if ty.TYPE_CHECKING:
    from gettext import gettext as _


def launch_argv_with_fallbacks(
    commands: list[str], print_error: bool = True
) -> bool:
    """Try the sequence of @commands with launch.spawn_async,
    and return with the first successful command.
    return False if no command is successful and log an error
    """
    for argv in commands:
        if ret := launch.spawn_async(argv):
            return ret

    pretty.print_error(__name__, "Unable to run command(s)", commands)
    return False


class CommandLeaf(RunnableLeaf):
    """The represented object of the CommandLeaf is a list of commandlines"""

    def run(self, ctx=None):
        launch_argv_with_fallbacks(self.object)


class Logout(CommandLeaf):
    """Log out from desktop"""

    def __init__(self, commands, name=None):
        super().__init__(commands, name or _("Log Out..."))

    def get_description(self):
        return _("Log out or change user")

    def get_icon_name(self):
        return "system-log-out"

    def run(self, ctx=None):
        if uiutils.confirm_dialog(_("Please confirm log out"), _("Log Out")):
            super().run(ctx)


class Shutdown(CommandLeaf):
    """Shutdown computer or reboot"""

    def __init__(self, commands, name=None):
        super().__init__(commands, name or _("Shut Down..."))

    def get_description(self):
        return _("Shut down, restart or suspend computer")

    def get_icon_name(self):
        return "system-shutdown"

    def run(self, ctx=None):
        if uiutils.confirm_dialog(
            _("Please confirm system shut down."), _("Shut down")
        ):
            super().run(ctx)


class LockScreen(CommandLeaf):
    """Lock screen"""

    def __init__(self, commands, name=None):
        super().__init__(commands, name or _("Lock Screen"))

    def get_description(self):
        return _("Enable screensaver and lock")

    def get_icon_name(self):
        return "system-lock-screen"


class CommonSource(Source):
    def is_dynamic(self):
        return True

    def get_icon_name(self):
        return "system-shutdown"

    def provides(self):
        yield RunnableLeaf
