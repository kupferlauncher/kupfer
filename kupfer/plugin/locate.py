__kupfer_name__ = _("Locate Files")
__kupfer_actions__ = ("Locate",)
__description__ = _("Search filesystem using locate")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import shutil
import subprocess
import typing as ty

from kupfer import icons, plugin_support
from kupfer.obj import Action, Leaf, Source, TextLeaf
from kupfer.obj.filesrc import construct_file_leaf
from kupfer.obj.special import CommandNotAvailableLeaf
from kupfer.support import kupferstring

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "ignore_case",
        "label": _("Ignore case distinctions when searching files"),
        "type": bool,
        "value": True,
    },
)

plugin_support.check_command_available("locate")


class Locate(Action):
    rank_adjust: int = -5

    def __init__(self):
        Action.__init__(self, _("Locate Files"))

    def is_factory(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        return LocateQuerySource(leaf.object)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search filesystem using locate")

    def get_gicon(self):
        return icons.ComposedIcon("gnome-terminal", self.get_icon_name())

    def get_icon_name(self):
        return "edit-find"


class LocateQuerySource(Source):
    def __init__(self, query):
        Source.__init__(self, name=_('Results for "%s"') % query)
        self.query = query
        self.max_items = 500

    def repr_key(self):
        return self.query

    def get_items(self):
        locate_cmd = shutil.which("locate")
        if not locate_cmd:
            yield CommandNotAvailableLeaf(__name__, __kupfer_name__, "locate")
            return

        ignore_case = (
            "--ignore-case" if __kupfer_settings__["ignore_case"] else ""
        )
        # Start two processes, one to take the first hits, one
        # to take the remaining up to maximum. We start both at the same time
        # (regrettably, locate wont output streamingly to stdout)
        # but we ask the second for results only after iterating the first few
        first_num = 12

        def load(limit: int, offset: int) -> ty.Iterator[Leaf]:
            command = [
                locate_cmd,
                "--null",
                "--limit",
                str(limit),
                ignore_case,
                self.query,
            ]
            with subprocess.Popen(command, stdout=subprocess.PIPE) as proc:
                out, ignored_err = proc.communicate()
                for f in out.split(b"\x00")[offset:-1]:
                    yield construct_file_leaf(kupferstring.fromlocale(f))

        yield from load(first_num, 0)
        yield from load(self.max_items, first_num)

    def get_gicon(self):
        return icons.ComposedIcon("gnome-terminal", self.get_icon_name())

    def get_icon_name(self):
        return "edit-find"
