from kupfer import pretty

class PluginSettings (pretty.OutputMixin):
	def __init__(self, *setdescs):
		self.setting_descriptions = {}
		req_keys = set(("key", "value", "type", "label"))
		for desc in setdescs:
			if not req_keys.issubset(desc.keys()):
				missing = req_keys.difference(desc.keys())
				raise KeyError("Plugin setting missing keys: %s" % missing)
			self.setting_descriptions[desc["key"]] = desc

	def __iter__(self):
		return iter(self.setting_descriptions)

	def __getitem__(self, key):
		self.output_debug("Getting", key)
		return self.setting_descriptions[key]["value"]
	def __setitem__(self, key, value):
		value_type = self.setting_descriptions[key]["type"]
		self.setting_descriptions[key]["value"] = value_type(value)

