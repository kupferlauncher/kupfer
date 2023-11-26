"""
This plugin for simplicity use cli interface instead of api, so we don't need
additional modules.
"""

from __future__ import annotations

__kupfer_name__ = _("tmux / tmuxp")
__kupfer_sources__ = ("TmuxSessionsSource", "TmuxpWorkspacesSource")
__description__ = _("Manage tmux and tmuxp sessions")
__version__ = "2023.1"
__author__ = "Karol Będkowski"

import datetime
import os
import typing as ty

from kupfer import launch, plugin_support
from kupfer.obj import Action, Leaf, Source
from kupfer.obj.helplib import FilesystemWatchMixin, FileMonitorToken

if ty.TYPE_CHECKING:
    from gettext import gettext as _

try:
    import libtmux
except ImportError:
    libtmux = None  # type: ignore

plugin_support.check_command_available("tmux")


class TmuxSession(Leaf):
    """Represented object is the session_id as string"""

    def __init__(
        self, sid: str, name: str, attached: str, created: str
    ) -> None:
        super().__init__(sid, name)
        self._attached = attached != "0"
        self._created = datetime.datetime.fromtimestamp(int(created))

    def get_actions(self):
        yield Attach()

    def get_description(self) -> str:
        return _("%(status)s tmux session, created %(time)s") % {
            "status": _("Attached") if self._attached else _("Detached"),
            "time": self._created,
        }

    def get_icon_name(self):
        return "gnome-window-manager"


def tmux_sessions(
    session_id: str | None = None,
) -> ty.Iterator[ty.Collection[str]]:
    if libtmux:
        if srv := libtmux.Server():  # type: ignore
            for sess in srv.sessions:
                if not sess.session_id:
                    continue

                yield (
                    sess.session_id,
                    sess.session_name or f"session {sess.session_id}",
                    sess.session_attached or "",
                    sess.session_created or "",
                )

            return

    # fallback
    cmd = (
        "tmux list-sessions -F "
        "'#{session_id}\t#{session_name}\t"
        "#{session_attached}\t#{session_created}'"
    )
    if session_id is not None:
        cmd += f" -f '#{{m:{session_id},#{{session_id}}}}'"

    with os.popen(cmd) as pipe:
        output = pipe.read()

    for line in output.splitlines():
        yield line.split("\t")


class TmuxSessionsSource(Source):
    """Source for tmux sessions"""

    source_use_cache = False

    def __init__(self):
        super().__init__(_("tmux Sessions"))

    def is_dynamic(self):
        return True

    def get_items(self):
        for session in tmux_sessions():
            yield TmuxSession(*session)

    def get_description(self):
        return _("Active tmux sessions")

    def get_icon_name(self):
        return "terminal"

    def provides(self):
        yield TmuxSession


class Attach(Action):
    def __init__(self):
        name = _("Attach")
        super().__init__(name)

    def activate(self, leaf, iobj=None, ctx=None):
        sid = leaf.object
        action_argv = ["tmux", "attach-session", "-t", sid, "-d"]
        launch.spawn_in_terminal(action_argv)


class TmuxpSession(Leaf):
    def __init__(self, name: str) -> None:
        super().__init__(name, name.capitalize())

    def get_actions(self):
        yield StartTmuxpSession()

    def get_description(self) -> str:
        return _("tmuxp saved session")

    def get_icon_name(self):
        return "gnome-window-manager"


class StartTmuxpSession(Action):
    def __init__(self):
        name = _("Start session")
        super().__init__(name)

    def activate(self, leaf, iobj=None, ctx=None):
        action_argv = ["tmuxp", "load", leaf.object]
        launch.spawn_in_terminal(action_argv)


class TmuxpWorkspacesSource(Source, FilesystemWatchMixin):
    """Source for tmuxp workspaces"""

    source_scan_interval: int = 3600
    _tmuxp_home = "~/.tmuxp/"

    def __init__(self):
        super().__init__(_("tmuxp Workspaces"))
        self._monitor_token: FileMonitorToken | None = None

    def initialize(self):
        tmux_ws_dir = os.path.expanduser(self._tmuxp_home)
        self._monitor_token = self.monitor_directories(tmux_ws_dir, force=True)

    def finalize(self):
        self.stop_monitor_fs_changes(self._monitor_token)

    def get_items(self):
        with os.popen("tmuxp ls") as pipe:
            output = pipe.read()

        for line in output.splitlines():
            if line := line.strip():
                yield TmuxpSession(line)

    def get_description(self):
        return _("Configured tmuxp workspaces")

    def get_icon_name(self):
        return "terminal"

    def provides(self):
        yield TmuxSession
