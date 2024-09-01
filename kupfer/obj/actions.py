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
from kupfer.obj.base import Action, Leaf
from kupfer.obj.exceptions import OperationError
from kupfer.obj.objects import RunnableLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _

    from kupfer.core import commandexec

__all__ = ("OpenUrl", "OpenTerminal", "Execute", "Perform")


class OpenTerminal(Action):
    action_accelerator = "t"

    def __init__(self, name: str = _("Open Terminal Here")) -> None:
        super().__init__(name)

    def wants_context(self) -> bool:
        return True

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert ctx
        try:
            launch.spawn_terminal(leaf.object, ctx.environment.get_screen())
            return None
        except SpawnError as exc:
            raise OperationError(exc) from exc

    def get_description(self) -> str | None:
        return _("Open this location in a terminal")

    def get_icon_name(self) -> str:
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

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        if self.quoted:
            argv = [leaf.object]
        else:
            argv = support.argv_for_commandline(leaf.object)
        if self.in_terminal:
            launch.spawn_in_terminal(argv)
        else:
            launch.spawn_async(argv)

        return None

    def get_description(self) -> str | None:
        if self.in_terminal:
            return _("Run this program in a Terminal")

        return _("Run this program")


class OpenUrl(Action):
    action_accelerator: str | None = "o"
    rank_adjust: int = 5

    def __init__(self, name: str = _("Open URL")) -> None:
        super().__init__(name)

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        url = leaf.object
        self.open_url(url)
        return None

    def open_url(self, url: str) -> None:
        launch.show_url(url)

    def get_description(self) -> str:
        return _("Open URL with default viewer")

    def get_icon_name(self) -> str:
        return "forward"


class Perform(Action):
    """Perform the action in a RunnableLeaf.

    RunnableLeaf can return result. In this case `has_result` and `item_types`
    must be specified.
    """

    action_accelerator: str | None = "o"
    rank_adjust = 5

    def __init__(
        self,
        name: str = _("Run"),
        has_result: bool = False,
        item_types: ty.Collection[Leaf] = (),
    ):
        # TRANS: 'Run' as in Perform a (saved) command
        super().__init__(name=name)
        self._has_result = has_result
        self._item_types = item_types

    def has_result(self):
        return self._has_result

    def wants_context(self) -> bool:
        return True

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert isinstance(leaf, RunnableLeaf)
        if leaf.wants_context():
            return ty.cast(ty.Optional[Leaf], leaf.run(ctx=ctx))

        return ty.cast(ty.Optional[Leaf], leaf.run())

    def get_description(self) -> str:
        return _("Perform command")

    def item_types(self):
        return self._item_types
