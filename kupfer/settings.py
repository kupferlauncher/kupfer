import os, sys
import ConfigParser

from kupfer import config

class SettingsController (object):
	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	sep = ";"
	default_directories = ("~/", "~/Desktop", )
	# Minimal "defaults" to define all fields
	# Read defaults defined in a defaults.cfg file
	defaults = {
		"Kupfer": { "Keybinding" : "" , "ShowStatusIcon" : "True" },
		"Plugins": { "Direct" : (), "Catalog" : (), },
		"Directories" : { "Direct" : default_directories, "Catalog" : (), },
		"DeepDirectories" : { "Direct" : (), "Catalog" : (), "Depth" : 1, },
	}
	def __init__(self):
		self.config = self._read_config()
	def _read_config(self):
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
		confmap = dict(self.defaults)
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
		for secname, section in confmap.iteritems():
			for key, default in section.iteritems():
				value = parser.get(secname, key)
				if isinstance(default, (tuple, list)):
					if not value:
						retval = ()
					else:
						retval = [p.strip() for p in value.split(self.sep) if p]
				elif isinstance(default, int):
					retval = type(default)(value)
				else:
					retval = str(value)
				confmap[secname][key] = retval

		return confmap
	def get_config(self, section, key):
		return self.config[section][key]

_settings_controller = None
def GetSettingsController():
	global _settings_controller
	if _settings_controller is None:
		_settings_controller = SettingsController()
	return _settings_controller
