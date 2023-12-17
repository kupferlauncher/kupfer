from __future__ import annotations

__kupfer_name__ = _("Kupfer Actions")
__kupfer_sources__ = ("KupferActions",)
__description__ = _(
    "'Inverse' action executions - look for action and then select object to "
    "execute on."
)
__version__ = "2023-12-17"
__author__ = "KB"


import typing as ty
from gettext import gettext as _

from kupfer import icons
from kupfer.core import sources, settings
from kupfer.obj import Source
from kupfer.obj.objects import ActionLeaf


class KupferActions(Source):
    """Get all global actions that don't require additional object."""

    def __init__(self):
        Source.__init__(self, _("Kupfer Actions"))

    def _on_plugin_enabled(
        self, _setctl: ty.Any, _plugin_id: str, _enabled: bool | int
    ) -> None:
        self.mark_for_update()

    def initialize(self):
        setctl = settings.get_settings_controller()
        setctl.connect("plugin-enabled-changed", self._on_plugin_enabled)

    def get_items(self):
        # we can skip action_generators
        sctl = sources.get_source_controller()
        for actions in sctl.action_decorators.values():
            for action in actions:
                # skip actions that require extra object
                if action.requires_object():
                    continue

                yield ActionLeaf(action)

    def get_gicon(self):
        return icons.ComposedIcon("kupfer", "kupfer-execute")
