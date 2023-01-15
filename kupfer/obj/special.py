__version__ = "2010-01-21"

import typing as ty

from kupfer.ui import preferences

from .objects import RunnableLeaf

if ty.TYPE_CHECKING:
    _ = str


class PleaseConfigureLeaf(RunnableLeaf):
    """Show information and allow to open preferences for given plugin"""

    message = _("Please Configure Plugin")
    description = _("Plugin %s is not configured")

    def __init__(self, plugin_id: str, plugin_name: str):
        plugin_id = plugin_id.split(".")[-1]
        RunnableLeaf.__init__(self, plugin_id, self.message)
        self.plugin_name = plugin_name

    def wants_context(self) -> bool:
        return True

    def run(self, ctx: ty.Any = None) -> None:
        assert ctx
        preferences.show_plugin_info(self.object, ctx.environment)

    def get_icon_name(self) -> str:
        return "preferences-desktop"

    def get_description(self) -> str:
        return self.description % self.plugin_name


class InvalidCredentialsLeaf(PleaseConfigureLeaf):
    description = _("Invalid user credentials for %s")
