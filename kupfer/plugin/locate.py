__kupfer_name__ = _("Locate Files")
__kupfer_actions__ = (
        "Locate",
    )
__description__ = _("Search filesystem using locate")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import subprocess

from kupfer.objects import Action, Source
from kupfer.objects import TextLeaf
from kupfer import icons, plugin_support
from kupfer import kupferstring
from kupfer.obj.objects import ConstructFileLeaf


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key" : "ignore_case",
        "label": _("Ignore case distinctions when searching files"),
        "type": bool,
        "value": True,
    },
)

class Locate (Action):
    def __init__(self):
        Action.__init__(self, _("Locate Files"))

    def is_factory(self):
        return True
    def activate(self, leaf):
        return LocateQuerySource(leaf.object)
    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return _("Search filesystem using locate")
    def get_gicon(self):
        return icons.ComposedIcon("gnome-terminal", self.get_icon_name())
    def get_icon_name(self):
        return "edit-find"

class LocateQuerySource (Source):
    def __init__(self, query):
        Source.__init__(self, name=_('Results for "%s"') % query)
        self.query = query
        self.max_items = 500

    def repr_key(self):
        return self.query

    def get_items(self):
        ignore_case = '--ignore-case' if __kupfer_settings__["ignore_case"] else ''
        # Start two processes, one to take the first hits, one
        # to take the remaining up to maximum. We start both at the same time
        # (regrettably, locate wont output streamingly to stdout)
        # but we ask the second for results only after iterating the first few
        first_num = 12
        first_command = ("locate --null --limit %d %s '%s'" %
                (first_num, ignore_case, self.query))
        full_command = ("locate --null --limit %d %s '%s'" %
                (self.max_items, ignore_case, self.query))
        p1 = subprocess.Popen(first_command, shell=True, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE)

        def get_locate_output(proc, offset=0):
            out, ignored_err = proc.communicate()
            return (ConstructFileLeaf(kupferstring.fromlocale(f))
                    for f in out.split(b'\x00')[offset:-1])

        for F in get_locate_output(p1, 0):
            yield F
        for F in get_locate_output(p2, first_num):
            yield F

    def get_gicon(self):
        return icons.ComposedIcon("gnome-terminal", self.get_icon_name())
    def get_icon_name(self):
        return "edit-find"
