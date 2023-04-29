"""
This plugin for simplicity use cli interface instead of api, so we don't need
additional modules.
"""

from __future__ import annotations

__kupfer_name__ = _("tmux / tmuxp")
__kupfer_sources__ = ("TmuxSessionsSource", "TmuxpSessionsSource")
__description__ = _("Manage tmux and tmuxp sessions")
__version__ = "2023.1"
__author__ = "Karol Będkowski"

import datetime
import os
import typing as ty

from kupfer import launch
from kupfer.obj import Action, Leaf, Source

if ty.TYPE_CHECKING:
    from getttext import gettext as _


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
        return _("%(status)s tmux session, created %(time)s") % {  # type:ignore
            "status": _("Attached") if self._attached else _("Detached"),
            "time": self._created,
        }

    def get_icon_name(self):
        return "gnome-window-manager"


def tmux_sessions(session_id: str | None = None) -> ty.Iterator[list[str]]:
    cmd = (
        "tmux list-sessions -F "
        "'#{session_id}\t#{session_name}\t"
        "#{session_attached}\t#{session_created}'"
    )
    if session_id is not None:
        cmd += f" -f '#{{m:{session_id},#{{session_id}}}}'"

    pipe = os.popen(cmd)
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
        return _("tmuxp saved session")  # type: ignore

    def get_icon_name(self):
        return "gnome-window-manager"


class StartTmuxpSession(Action):
    def __init__(self):
        name = _("Start session")
        super().__init__(name)

    def activate(self, leaf, iobj=None, ctx=None):
        action_argv = ["tmuxp", "load", leaf.object]
        launch.spawn_in_terminal(action_argv)


class TmuxpSessionsSource(Source):
    """Source for tmuxp sessions"""

    def __init__(self):
        super().__init__(_("tmuxp Sessions"))

    def get_items(self):
        pipe = os.popen("tmuxp ls")
        output = pipe.read()
        for line in output.splitlines():
            if line := line.strip():
                yield TmuxpSession(line)

    def get_description(self):
        return _("Active tmux sessions")

    def get_icon_name(self):
        return "terminal"

    def provides(self):
        yield TmuxSession
