__kupfer_name__ = _("GNU Screen")
__kupfer_sources__ = ("ScreenSessionsSource",)
__description__ = _("Active GNU Screen sessions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import pwd
import typing as ty
from pathlib import Path

from kupfer import launch, plugin_support
from kupfer.obj import Action, Leaf, Source
from kupfer.obj.helplib import FilesystemWatchMixin

if ty.TYPE_CHECKING:
    from gettext import gettext as _

plugin_support.check_command_available("screen")


def screen_sessions_infos():
    """
    Yield tuples of pid, name, time, status
    for running screen sessions
    """
    with os.popen("screen -list") as pipe:
        output = pipe.read()

    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) == 4:  # noqa:PLR2004
            _empty, pidname, time, status = fields
            pid, name = pidname.split(".", 1)
            time = time.strip("()")
            status = status.strip("()")
            yield (pid, name, time, status)


def get_username():
    """Return username for current user"""
    info = pwd.getpwuid(os.geteuid())
    return info[0]


class ScreenSession(Leaf):
    """Represented object is the session pid as string"""

    def get_actions(self):
        return (AttachScreen(),)

    def is_valid(self):
        for pid, *_rest in screen_sessions_infos():
            if self.object == pid:
                return True

        return False

    def get_description(self):
        for pid, _name, time, status in screen_sessions_infos():
            if self.object == pid:
                # Handle localization of status
                status_human = status
                if status == "Attached":
                    status_human = _("Attached")
                elif status == "Detached":
                    status_human = _("Detached")

                return _("%(status)s session (%(pid)s) created %(time)s") % {
                    "status": status_human,
                    "pid": pid,
                    "time": time,
                }

        return f"{self.name} ({self.object})"

    def get_icon_name(self):
        return "gnome-window-manager"


class ScreenSessionsSource(Source, FilesystemWatchMixin):
    """Source for GNU Screen sessions"""

    source_scan_interval: int = 3600

    def __init__(self):
        super().__init__(_("Screen Sessions"))
        self.screen_dir = None
        self.monitor_token = None

    def initialize(self):
        ## the screen dir might not exist when we start
        ## luckily, gio can monitor directories before they exist
        self.screen_dir = (
            os.getenv("SCREENDIR") or f"/var/run/screen/S-{get_username()}"
        )
        if not Path(self.screen_dir).exists():
            self.output_debug("Screen socket dir or SCREENDIR not found")

        self.monitor_token = self.monitor_directories(
            self.screen_dir, force=True
        )

    def get_items(self):
        assert self.screen_dir
        if not Path(self.screen_dir).exists():
            return

        for pid, name, _time, _status in screen_sessions_infos():
            yield ScreenSession(pid, name)

    def get_description(self):
        return _("Active GNU Screen sessions")

    def get_icon_name(self):
        return "terminal"

    def provides(self):
        yield ScreenSession


class AttachScreen(Action):
    def __init__(self):
        super().__init__(name=_("Attach"))

    def activate(self, leaf, iobj=None, ctx=None):
        pid = leaf.object
        action_argv = ["screen", "-x", "-R", str(pid)]
        launch.spawn_in_terminal(action_argv)
