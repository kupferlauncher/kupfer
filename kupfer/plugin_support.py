from kupfer import pretty, settings

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
		req_keys = set(("key", "value", "type", "label"))
		for desc in setdescs:
			if not req_keys.issubset(desc.keys()):
				missing = req_keys.difference(desc.keys())
				raise KeyError("Plugin setting missing keys: %s" % missing)
			self.setting_descriptions[desc["key"]] = desc

	def __iter__(self):
		return iter(self.setting_descriptions)

	def initialize(self, plugin_name):
		"""Init by reading from global settings and setting up callbacks"""
		setctl = settings.GetSettingsController()
		for key in self:
			value_type = self.setting_descriptions[key]["type"]
			value = setctl.get_plugin_config(plugin_name, key, value_type)
			if value is not None:
				self[key] = value
		setctl.connect("value-changed", self._value_changed)

	def __getitem__(self, key):
		return self.setting_descriptions[key]["value"]
	def __setitem__(self, key, value):
		value_type = self.setting_descriptions[key]["type"]
		self.setting_descriptions[key]["value"] = value_type(value)
	def _value_changed(self, setctl, section, key, value):
		"""Preferences changed, update object"""
		if key in self:
			self[key] = value
	def get_value_type(self, key):
		"""Return type of setting @key"""
		return self.setting_descriptions[key]["type"]
	def get_label(self, key):
		"""Return label for setting @key"""
		return self.setting_descriptions[key]["label"]
