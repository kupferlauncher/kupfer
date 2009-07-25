from kupfer import pretty, settings

class PluginSettings (pretty.OutputMixin):
	def __init__(self, *setdescs):
		"""Check if passed-in dictionaries have all required keys"""
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
		# FIXME: We should set up preference key changed callbacks here
		for key in self:
			value_type = self.setting_descriptions[key]["type"]
			value = setctl.get_plugin_config(plugin_name, key, value_type)
			if value is not None:
				self[key] = value

	def __getitem__(self, key):
		return self.setting_descriptions[key]["value"]
	def __setitem__(self, key, value):
		value_type = self.setting_descriptions[key]["type"]
		self.setting_descriptions[key]["value"] = value_type(value)
