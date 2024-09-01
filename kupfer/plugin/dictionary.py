__kupfer_name__ = _("Dictionary")
__kupfer_actions__ = ("LookUp",)
__description__ = _("Look up word in dictionary")
__version__ = "2023-04-14"
__author__ = "Ulrik, KB"

import shutil
import typing as ty

from kupfer import launch, plugin_support
from kupfer.desktop_launch import SpawnError
from kupfer.obj import Action, OperationError, TextLeaf

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class Dict(ty.NamedTuple):
    title: str
    args: list[str]


dictionaries = {
    "gnome-dictionary": Dict(
        _("Gnome Dictionary"), ["gnome-dictionary", "--look-up=%s"]
    ),
    "mate-dictionary": Dict(
        _("Mate Dictionary"), ["mate-dictionary", "--look-up=%s"]
    ),
    "purple": Dict(_("Purple"), ["purple", "--define=%s"]),
    "xfce4-dict": Dict(_("Xfce4 Dict"), ["xfce4-dict", "--dict", "%s"]),
    "org.goldendict.GoldenDict": Dict(_("GoldenDict"), ["goldendict", "%s"]),
}

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "dictionary",
        "label": _("Dictionary"),
        "type": str,
        "alternatives": [(key, dic.title) for key, dic in dictionaries.items()],
        "value": "gnome-dictionary",
    }
)


class LookUp(Action):
    def __init__(self):
        Action.__init__(self, _("Look Up"))

    def activate(self, leaf, iobj=None, ctx=None):
        text = leaf.object
        dict_id = __kupfer_settings__["dictionary"]
        dict_def = dictionaries[dict_id]

        if not shutil.which(dict_def.args[0]):
            raise OperationError(f"{dict_def.title} not available")

        dict_argv = [arg.replace("%s", text) for arg in dict_def.args]
        try:
            launch.spawn_async_notify_as(dict_id + ".desktop", dict_argv)
        except SpawnError as exc:
            raise OperationError(exc) from exc

    def item_types(self):
        yield TextLeaf

    def valid_for_item(self, leaf):
        text = leaf.object
        return len(text.split("\n", 1)) <= 1

    def get_description(self):
        curr_dict = __kupfer_settings__["dictionary"]
        return _("Look up word in %s") % dictionaries[curr_dict].title

    def get_icon_name(self):
        return "accessories-dictionary"
