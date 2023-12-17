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
from kupfer.core import sources
from kupfer.obj import Action, Leaf, Source


class ExecuteAction(Action):
    """Execute action selected as leaf on iobj."""

    def __init__(self, action: Action) -> None:
        super().__init__(name=_("Run On..."))
        self.action = action

    def wants_context(self) -> bool:
        return self.action.wants_context()

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj

        self.action.activate(iobj, ctx=ctx)

    def requires_object(self):
        return True

    def object_types(self):
        yield from self.action.item_types()

    def valid_object(self, iobj, for_item=None):
        return self.action.valid_for_item(iobj)

    def repr_key(self) -> ty.Any:
        return self.action


class ActionLeaf(Leaf):
    def __init__(self, action: Action):
        Leaf.__init__(self, action, action.name)

    def get_actions(self):
        return (ExecuteAction(self.object),)

    def get_gicon(self):
        return self.object.get_gicon()

    def get_icon_name(self):
        return self.object.get_icon_name()

    def repr_key(self) -> ty.Any:
        return self.object

    def get_description(self):
        return self.object.get_description()


class KupferActions(Source):
    """Get all global actions that don't require additional object."""

    def __init__(self):
        Source.__init__(self, _("Kupfer Actions"))

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
