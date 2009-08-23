import os, sys
import ConfigParser
import copy

import gobject

from kupfer import config, pretty, scheduler

def strbool(value, default=False):
	"""Coarce bool from string value or bool"""
	if value in (True, False):
		return value
	value = str(value).lower()
	if value in ("no", "false"):
		return False
	if value in ("yes", "true"):
		return True
	return default

class SettingsController (gobject.GObject, pretty.OutputMixin):
	__gtype_name__ = "SettingsController"
	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	sep = ";"
	default_directories = ("~/", "~/Desktop", )
	# Minimal "defaults" to define all fields
	# Read defaults defined in a defaults.cfg file
	defaults = {
		"Kupfer": { "keybinding" : "" , "showstatusicon" : "true" },
		"Directories" : { "direct" : default_directories, "catalog" : (), },
		"DeepDirectories" : { "direct" : (), "catalog" : (), "depth" : 1, },
	}
	def __init__(self):
		gobject.GObject.__init__(self)
		self._config = self._read_config()
		self._save_timer = scheduler.Timer(True)

	def _update_config_save_timer(self):
		self._save_timer.set(60, self._save_config)

	def _read_config(self, read_config=True):
		"""
		Read cascading config files
		default -> then config
		(in all XDG_CONFIG_DIRS)
		"""
		parser = ConfigParser.SafeConfigParser()

		def fill_parser(parser, defaults):
			for secname, section in defaults.iteritems():
				if not parser.has_section(secname):
					parser.add_section(secname)
				for key, default in section.iteritems():
					if isinstance(default, (tuple, list)):
						default = self.sep.join(default)
					elif isinstance(default, int):
						default = str(default)
					parser.set(secname, key, default)

		# Set up defaults
		confmap = copy.deepcopy(self.defaults)
		fill_parser(parser, confmap)

		# Read all config files
		config_files = []
		defaults_path = config.get_data_file(self.defaults_filename)
		if not defaults_path:
			# try local file
			defaults_path = os.path.join("data", self.defaults_filename)
		if not os.path.exists(defaults_path):
			print "Error: no default config file %s found!" % self.defaults_filename
		else:
			config_files += (defaults_path, )

		if read_config:
			config_path = config.get_config_file(self.config_filename)
			if config_path:
				config_files += (config_path, )

		for config_file in config_files:
			try:
				fil = open(config_file, "r")
				parser.readfp(fil)
				fil.close()
			except IOError, e:
				print "Error reading configuration file %s: %s", (config_file, e)

		# Read parsed file into the dictionary again
		for secname in parser.sections():
			if secname not in confmap: confmap[secname] = {}
			for key in parser.options(secname):
				value = parser.get(secname, key)
				retval = value
				if secname in self.defaults and key in self.defaults[secname]:
					defval = self.defaults[secname][key]
					if isinstance(defval, (tuple, list)):
						if not value:
							retval = ()
						else:
							retval = [p.strip() for p in value.split(self.sep) if p]
					elif isinstance(defval, int):
						retval = type(defval)(value)
					else:
						retval = str(value)
				confmap[secname][key] = retval

		return confmap

	def _save_config(self, scheduler=None):
		self.output_debug("Saving config")
		config_path = config.save_config_file(self.config_filename)
		if not config_path:
			self.output_info("Unable to save settings, can't find config dir")
			return
		# read in just the default values
		default_confmap = self._read_config(read_config=False)

		def confmap_difference(config, defaults):
			"""Extract the non-default keys to write out"""
			difference = dict()
			for secname, section in config.items():
				if secname not in defaults:
					difference[secname] = dict(section)
					continue
				difference[secname] = {}
				for key, config_val in section.items():
					if (secname in defaults and
							key in defaults[secname]):
						if defaults[secname][key] == config_val:
							continue
					difference[secname][key] = config_val
				if not difference[secname]:
					del difference[secname]
			return difference

		parser = ConfigParser.SafeConfigParser()
		def fill_parser(parser, defaults):
			for secname, section in defaults.iteritems():
				if not parser.has_section(secname):
					parser.add_section(secname)
				for key, default in section.iteritems():
					if isinstance(default, (tuple, list)):
						default = self.sep.join(default)
					elif isinstance(default, int):
						default = str(default)
					parser.set(secname, key, default)

		confmap = confmap_difference(self._config, default_confmap)
		fill_parser(parser, confmap)
		out = open(config_path, "w")
		parser.write(out)

	def get_config(self, section, key):
		"""General interface, but section must exist"""
		key = key.lower()
		value = self._config[section].get(key)
		if section in self.defaults and key in self.defaults[section]:
			return value
		else:
			self.output_info("Settings key", section, key, "is invalid")

	def _set_config(self, section, key, value):
		"""General interface, but section must exist"""
		self.output_debug("Set", section, key, "to", value)
		key = key.lower()
		oldvalue = self._config[section].get(key)
		if section in self.defaults and key in self.defaults[section]:
			value_type = type(oldvalue)
			self._config[section][key] = value_type(value)
			self.emit("value-changed", section, key, value)
			self._update_config_save_timer()
			return True
		self.output_info("Settings key", section, key, "is invalid")
		return False

	def _get_raw_config(self, section, key):
		"""General interface, but section must exist"""
		key = key.lower()
		value = self._config[section].get(key)
		return value

	def _set_raw_config(self, section, key, value):
		"""General interface, but will create section"""
		self.output_debug("Set", section, key, "to", value)
		key = key.lower()
		if section not in self._config:
			self._config[section] = {}
		self._config[section][key] = str(value)
		self._update_config_save_timer()
		return False

	def get_plugin_enabled(self, plugin_id):
		"""Convenience: if @plugin_id is enabled"""
		return self.get_plugin_config(plugin_id, "kupfer_enabled",
				value_type=strbool, default=False)

	def set_plugin_enabled(self, plugin_id, enabled):
		"""Convenience: set if @plugin_id is enabled"""
		return self.set_plugin_config(plugin_id, "kupfer_enabled", enabled,
				value_type=strbool)

	def get_plugin_is_toplevel(self, plugin_id):
		"""Convenience: if @plugin_id items are included in toplevel"""
		return self.get_plugin_config(plugin_id, "kupfer_toplevel",
				value_type=strbool, default=True)

	def get_plugin_show_toplevel_option(self, plugin_id):
		"""Convenience: if @plugin_id should show toplevel option"""
		return self.get_plugin_config(plugin_id, "kupfer_show_toplevel",
				value_type=strbool, default=False)

	def get_plugin_is_hidden(self, plugin_id):
		"""Convenience: if @plugin_id is hidden"""
		return self.get_plugin_config(plugin_id, "kupfer_hidden",
				value_type=strbool, default=False)

	def get_keybinding(self):
		"""Convenience: Kupfer keybinding as string"""
		return self.get_config("Kupfer", "keybinding")

	def set_keybinding(self, keystr):
		"""Convenience: Set Kupfer keybinding as string"""
		return self._set_config("Kupfer", "keybinding", keystr)

	def get_show_status_icon(self):
		"""Convenience: Show icon in notification area as bool"""
		return (self.get_config("Kupfer", "showstatusicon").lower()
				in ("true", "yes"))
	def set_show_status_icon(self, enabled):
		"""Set config value and return success"""
		return self._set_config("Kupfer", "showstatusicon", enabled)

	def get_plugin_config(self, plugin, key, value_type=str, default=None):
		"""Return setting @key for plugin names @plugin, try
		to coerce to type @value_type.
		Else return @default if does not exist, or can't be coerced
		"""
		plug_section = "plugin_%s" % plugin
		if not plug_section in self._config:
			return default
		val = self._get_raw_config(plug_section, key)

		if val is None:
			return default

		if value_type is bool:
			value_type = strbool

		try:
			val = value_type(val)
		except ValueError, err:
			self.output_info("Error for stored value %s.%s" %
					(plug_section, key), err)
			return default
		return val

	def set_plugin_config(self, plugin, key, value, value_type=str):
		"""Try set @key for plugin names @plugin, coerce to @value_type
		first.  """
		plug_section = "plugin_%s" % plugin
		self.emit("value-changed", plug_section, key, value)
		return self._set_raw_config(plug_section, key, value_type(value))

# Section, Key, Value
gobject.signal_new("value-changed", SettingsController, gobject.SIGNAL_RUN_LAST,
	gobject.TYPE_BOOLEAN, (gobject.TYPE_STRING, gobject.TYPE_STRING,
		gobject.TYPE_PYOBJECT))

_settings_controller = None
def GetSettingsController():
	global _settings_controller
	if _settings_controller is None:
		_settings_controller = SettingsController()
	return _settings_controller
