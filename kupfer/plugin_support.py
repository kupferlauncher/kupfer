from kupfer import pretty
from kupfer.core import settings
from kupfer.core.settings import UserNamePassword

SETTING_PREFER_CATALOG = {
	"key" : "kupfer_toplevel",
	"label": _("Include in top level"),
	"type": bool,
	"value": False,
	"tooltip": _(
		"If enabled, objects from the plugin's source(s) "
		"will be available in the top level.\n"
		"Sources are always available as subcatalogs in the top level."),
}

def _is_core_setting(key):
	return key.startswith("kupfer_")

class PluginSettings (pretty.OutputMixin):
	"""Allows plugins to have preferences by assigning an instance
	of this class to the plugin's __kupfer_settings__ attribute.

	Setting values are accessed by the getitem operator [] with
	the setting's 'key' attribute
	"""
	def __init__(self, *setdescs):
		"""Create a settings collection by passing in dictionaries
		as arguments, where each dictionary must have the following keys:
			key
			type
			value (default value)
			label (localized label)

		the @key may be any string except strings starting with
		'kupfer_', which are reserved
		"""
		self.setting_descriptions = {}
		self.setting_key_order = []
		req_keys = set(("key", "value", "type", "label"))
		for desc in setdescs:
			if not req_keys.issubset(desc.keys()):
				missing = req_keys.difference(desc.keys())
				raise KeyError("Plugin setting missing keys: %s" % missing)
			self.setting_descriptions[desc["key"]] = dict(desc)
			self.setting_key_order.append(desc["key"])

	def __iter__(self):
		return iter(self.setting_key_order)

	def initialize(self, plugin_name):
		"""Init by reading from global settings and setting up callbacks"""
		setctl = settings.GetSettingsController()
		for key in self:
			value_type = self.setting_descriptions[key]["type"]
			value = setctl.get_plugin_config(plugin_name, key, value_type)
			if value is not None:
				self[key] = value
			elif _is_core_setting(key):
				default = self.setting_descriptions[key]["value"]
				setctl.set_plugin_config(plugin_name, key, default, value_type)
		setctl.connect("value-changed", self._value_changed, plugin_name)

	def __getitem__(self, key):
		return self.setting_descriptions[key]["value"]
	def __setitem__(self, key, value):
		value_type = self.setting_descriptions[key]["type"]
		self.setting_descriptions[key]["value"] = value_type(value)
	def _value_changed(self, setctl, section, key, value, plugin_name):
		"""Preferences changed, update object"""
		if key in self and plugin_name in section:
			self[key] = value
	def get_value_type(self, key):
		"""Return type of setting @key"""
		return self.setting_descriptions[key]["type"]
	def get_label(self, key):
		"""Return label for setting @key"""
		return self.setting_descriptions[key]["label"]
	def get_alternatives(self, key):
		"""Return alternatives for setting @key (if any)"""
		return self.setting_descriptions[key].get("alternatives")
	def get_tooltip(self, key):
		"""Return tooltip string for setting @key (if any)"""
		return self.setting_descriptions[key].get("tooltip")

# Plugin convenience functions for dependencies

_has_dbus_connection = None

def check_dbus_connection():
	"""
	Check if a connection to the D-Bus daemon is available,
	else raise ImportError with an explanatory error message.

	For plugins that can not be used without contact with D-Bus;
	if this check is used, the plugin may use D-Bus and assume it
	is available in the Plugin's code.
	"""
	global _has_dbus_connection
	if _has_dbus_connection is None:
		import dbus
		try:
			dbus.Bus()
			_has_dbus_connection = True
		except dbus.DBusException, err:
			_has_dbus_connection = False
	if not _has_dbus_connection:
		raise ImportError(_("No D-Bus connection to desktop session"))



