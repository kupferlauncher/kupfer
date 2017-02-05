__kupfer_name__ = _("Kupfer Plugins")
__kupfer_sources__ = ("KupferPlugins", )
__description__ = _("Access Kupfer's plugin list in Kupfer")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

from kupfer.objects import Action, Source, Leaf, FileLeaf, TextLeaf
from kupfer import kupferui

# Since this is a core plugin we break some rules
# These modules are normally out of bounds for plugins
from kupfer.core import plugins, settings


class ShowInfo (Action):
    def __init__(self):
        Action.__init__(self, _("Show Information"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        plugin_id = leaf.object["name"]
        kupferui.show_plugin_info(plugin_id, ctx.environment)

    def get_description(self):
        pass
    def get_icon_name(self):
        return "dialog-information"

class ShowSource (Action):
    def __init__(self):
        Action.__init__(self, _("Show Source Code"))

    def has_result(self):
        return True
    def activate(self, leaf):
        # Try to find the __file__ attribute for the plugin
        # It will fail for files inside zip packages, but that is
        # uncommon for now.
        # Additionally, it will fail for fake plugins
        plugin_id = leaf.object["name"]
        filename = plugins.get_plugin_attribute(plugin_id, "__file__")
        if not filename:
            return leaf
        root, ext = os.path.splitext(filename)
        if ext.lower() == ".pyc" and os.path.exists(root + ".py"):
            return FileLeaf(root + ".py")

        if not os.path.exists(filename):
            # handle modules in zip or eggs
            import pkgutil
            pfull = "kupfer.plugin." + plugin_id
            loader = pkgutil.get_loader(pfull)
            if loader:
                return TextLeaf(loader.get_source(pfull))
        return FileLeaf(filename)

    def get_description(self):
        pass
    def get_icon_name(self):
        return "dialog-information"

class Plugin (Leaf):
    # NOTE: Just to be sure that a plugin ranks lower than a
    # like-named other object by default.
    rank_adjust = -1
    def __init__(self, obj, name):
        Leaf.__init__(self, obj, name)
    def get_actions(self):
        yield ShowInfo()
        yield ShowSource()

    def get_description(self):
        setctl = settings.GetSettingsController()
        enabled = setctl.get_plugin_enabled(self.object["name"])
        return "%s (%s)" % (self.object["description"],
                _("enabled") if enabled else _("disabled"))
    def get_icon_name(self):
        return "package-x-generic"

class KupferPlugins (Source):
    def __init__(self):
        Source.__init__(self, _("Kupfer Plugins"))

    def get_items(self):
        setctl = settings.GetSettingsController()
        for info in plugins.get_plugin_info():
            plugin_id = info["name"]
            if setctl.get_plugin_is_hidden(plugin_id):
                continue
            yield Plugin(info, info["localized_name"])

    def should_sort_lexically(self):
        return True

    def provides(self):
        yield Plugin

    def get_icon_name(self):
        return "package-x-generic"

    @classmethod
    def decorates_type(cls):
        return Plugin

    @classmethod
    def decorate_item(cls, obj):
        if cls.is_self_plugin(obj):
            return cls()

    @classmethod
    def is_self_plugin(cls, obj):
        self_plug_id = __name__.split(".")[-1]
        return obj.object['name'] == self_plug_id

    def get_leaf_repr(self):
        for obj in self.get_leaves():
            if self.is_self_plugin(obj):
                return obj

