__kupfer_name__ = _("Devhelp")
__kupfer_actions__ = ("LookUp", )
__description__ = _("Search in Devhelp")
__version__ = "2017.1"
__author__ = ""

from kupfer.objects import Action, TextLeaf, OperationError
from kupfer import utils


class LookUp (Action):
    def __init__(self):
        Action.__init__(self, _("Search in Devhelp"))
    def activate(self, leaf):
        text = leaf.object
        try:
            utils.spawn_async_raise(['devhelp', '--search=%s' % text])
        except utils.SpawnError as exc:
            raise OperationError(exc)
    def item_types(self):
        yield TextLeaf
    def valid_for_item(self, leaf):
        text = leaf.object
        return '\n' not in text
    def get_description(self):
        return None
    def get_icon_name(self):
        return "devhelp"
