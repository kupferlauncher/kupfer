__kupfer_name__ = _("Devhelp")
__kupfer_actions__ = ("LookUp",)
__description__ = _("Search in Devhelp")
__version__ = "2017.1"
__author__ = ""

from kupfer import launch
from kupfer.obj import Action, OperationError, TextLeaf


class LookUp(Action):
    def __init__(self):
        Action.__init__(self, _("Search in Devhelp"))

    def activate(self, leaf, iobj=None, ctx=None):
        text = leaf.object
        try:
            launch.spawn_async_raise(["devhelp", f"--search={text}"])
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        text = leaf.object
        return "\n" not in text

    def get_description(self):
        return None

    def get_icon_name(self):
        return "devhelp"
