"""
Global actions.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty

from kupfer import launch, support
from kupfer.desktop_launch import SpawnError

from .base import Action
from .exceptions import OperationError

__all__ = ("OpenUrl", "OpenTerminal", "Execute", "Perform")

if ty.TYPE_CHECKING:
    _ = str


class OpenTerminal(Action):
    action_accelerator = "t"

    def __init__(self, name=_("Open Terminal Here")):
        super().__init__(name)

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        try:
            launch.spawn_terminal(leaf.object, ctx.environment.get_screen())
        except SpawnError as exc:
            raise OperationError(exc) from exc

    def get_description(self) -> str | None:
        return _("Open this location in a terminal")

    def get_icon_name(self):
        return "utilities-terminal"


class Execute(Action):
    """Execute executable file (FileLeaf)"""

    rank_adjust = 10

    def __init__(self, in_terminal=False, quoted=True):
        name = _("Run in Terminal") if in_terminal else _("Run (Execute)")
        super().__init__(name)
        self.in_terminal = in_terminal
        self.quoted = quoted

    def repr_key(self):
        return (self.in_terminal, self.quoted)

    def activate(self, leaf, iobj=None, ctx=None):
        if self.quoted:
            argv = [leaf.object]
        else:
            argv = support.argv_for_commandline(leaf.object)
        if self.in_terminal:
            launch.spawn_in_terminal(argv)
        else:
            launch.spawn_async(argv)

    def get_description(self) -> str | None:
        if self.in_terminal:
            return _("Run this program in a Terminal")

        return _("Run this program")


class OpenUrl(Action):
    action_accelerator: str | None = "o"
    rank_adjust: int = 5

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or _("Open URL"))

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        url = leaf.object
        self.open_url(url)

    def open_url(self, url: str) -> None:
        launch.show_url(url)

    def get_description(self) -> str:
        return _("Open URL with default viewer")

    def get_icon_name(self) -> str:
        return "forward"


class Perform(Action):
    """Perform the action in a RunnableLeaf"""

    action_accelerator: str | None = "o"
    rank_adjust = 5

    def __init__(self, name: str | None = None):
        # TRANS: 'Run' as in Perform a (saved) command
        super().__init__(name=name or _("Run"))

    def wants_context(self) -> bool:
        return True

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        if leaf.wants_context():
            leaf.run(ctx=ctx)
            return

        leaf.run()

    def get_description(self) -> str:
        return _("Perform command")
