import os

from kupfer.objects import Action, Source, Leaf, FileLeaf
from kupfer import plugin_support

# Since this is a core plugin we break some rules
# This module is normally out of bounds for plugins
from kupfer import plugins, settings

__kupfer_name__ = _("Kupfer Plugins")
__kupfer_sources__ = ("KupferPlugins", )
__description__ = _("Access Kupfer's plugin list in Kupfer")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)

class ShowInfo (Action):
	def __init__(self):
		Action.__init__(self, _("Show Information"))
	def activate(self, leaf):
		from kupfer import preferences
		prefs = preferences.GetPreferencesWindowController()
		plugin_id = leaf.object["name"]
		prefs.show_focus_plugin(plugin_id)

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
		print filename
		root, ext = os.path.splitext(filename)
		if ext.lower() == ".pyc" and os.path.exists(root + ".py"):
			return FileLeaf(root + ".py")
		return FileLeaf(filename)

	def get_description(self):
		pass
	def get_icon_name(self):
		return "dialog-information"

class Plugin (Leaf):
	def __init__(self, obj, name):
		Leaf.__init__(self, obj, name)
		self.name_aliases.add(self.get_description())
	def get_actions(self):
		yield ShowInfo()
		yield ShowSource()

	def get_description(self):
		setctl = settings.GetSettingsController()
		enabled = setctl.get_plugin_enabled(self.object["name"])
		return _("%s (%s)") % (self.object["description"],
				_("enabled") if enabled else _("disabled"))
	def get_icon_name(self):
		return "package"

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
		return "search"

