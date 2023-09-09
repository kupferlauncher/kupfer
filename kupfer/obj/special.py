"""
Special objects.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

from gettext import gettext as _

from kupfer.ui import preferences
from kupfer.obj.objects import RunnableLeaf
from kupfer.core import commandexec

__version__ = "2023-09-09"
__all__ = (
    "PleaseConfigureLeaf",
    "InvalidCredentialsLeaf",
    "NonfunctionalLeaf",
    "CommandNotAvailableLeaf",
)


class PleaseConfigureLeaf(RunnableLeaf):
    """Show information and allow to open preferences for given plugin"""

    message = _("Please Configure Plugin")
    description = _("Plugin %s is not configured")

    def __init__(self, plugin_id: str, plugin_name: str) -> None:
        plugin_id = plugin_id.split(".")[-1]
        RunnableLeaf.__init__(self, plugin_id, self.message)
        self.plugin_name = plugin_name

    def wants_context(self) -> bool:
        return True

    def run(self, ctx: commandexec.ExecutionToken | None = None) -> None:
        assert ctx
        preferences.show_plugin_info(self.object, ctx.environment)

    def get_icon_name(self) -> str:
        return "preferences-desktop"

    def get_description(self) -> str:
        return self.description % self.plugin_name


class InvalidCredentialsLeaf(PleaseConfigureLeaf):
    description = _("Invalid user credentials for %s")


class NonfunctionalLeaf(PleaseConfigureLeaf):
    """Leaf with custom error message that open plugin preferences dialog."""

    def __init__(
        self, plugin_id: str, plugin_name: str, description: str
    ) -> None:
        super().__init__(plugin_id, plugin_name)
        self.description = description

    def get_description(self) -> str:
        return self.description


class CommandNotAvailableLeaf(PleaseConfigureLeaf):
    """Leaf with message "command ... not available" that open plugin
    preferences dialog."""

    description = _("Command '%s' not available")

    def __init__(self, plugin_id: str, plugin_name: str, command: str) -> None:
        super().__init__(plugin_id, plugin_name)
        self.command = command

    def get_description(self) -> str:
        return self.description % self.command
