__kupfer_name__ = _("Dictionary")
__kupfer_actions__ = ("LookUp", )
__description__ = _("Look up word in dictionary")
__version__ = ""
__author__ = "Ulrik"

from kupfer.objects import Action, TextLeaf, OperationError
from kupfer import utils
from kupfer import plugin_support

dictionaries = {
    'gnome-dictionary': ['gnome-dictionary', '--look-up='],
    'purple': ['purple', '--define='],
    'xfce4-dict': ['xfce4-dict', '--dict', ''],
}

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "dictionary",
        "label": _("Dictionary"),
        "type": str,
        "alternatives": list(dictionaries.keys()),
        "value": 'gnome-dictionary',
    }
)

class LookUp (Action):
    def __init__(self):
        Action.__init__(self, _("Look Up"))
    def activate(self, leaf):
        text = leaf.object
        dict_id = __kupfer_settings__["dictionary"]
        dict_argv = list(dictionaries[dict_id])
        dict_argv[-1] = dict_argv[-1] + text
        try:
            utils.spawn_async_notify_as(dict_id + ".desktop", dict_argv)
        except utils.SpawnError as exc:
            raise OperationError(exc)

    def item_types(self):
        yield TextLeaf
    def valid_for_item(self, leaf):
        text = leaf.object
        return len(text.split("\n", 1)) <= 1
    def get_description(self):
        return _("Look up word in dictionary")
    def get_icon_name(self):
        return "accessories-dictionary"
