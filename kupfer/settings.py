import os, sys
import ConfigParser

from kupfer import config

def get_config():
	"""
	Read cascading config files
	default -> then config
	(in all XDG_CONFIG_DIRS)
	"""

	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	sep = ";"
	parser = ConfigParser.SafeConfigParser()
	default_directories = ("~/", "~/Desktop", )
	# Minimal "defaults" to define all fields
	# Read defaults defined in a defaults.cfg file
	defaults = {
		"Kupfer": { "Keybinding" : "" , "ShowStatusIcon" : "True" },
		"Plugins": { "Direct" : (), "Catalog" : (), },
		"Directories" : { "Direct" : default_directories, "Catalog" : (), },
		"DeepDirectories" : { "Direct" : (), "Catalog" : (), "Depth" : 1, },
	}

	def fill_parser(parser, defaults):
		for secname, section in defaults.iteritems():
			if not parser.has_section(secname):
				parser.add_section(secname)
			for key, default in section.iteritems():
				if isinstance(default, (tuple, list)):
					default = sep.join(default)
				elif isinstance(default, int):
					default = str(default)
				parser.set(secname, key, default)

	# Set up defaults
	fill_parser(parser, defaults)

	# Read all config files
	config_files = []
	defaults_path = config.get_data_file(defaults_filename)
	if not defaults_path:
		# try local file
		defaults_path = os.path.join("data", defaults_filename)
	if not os.path.exists(defaults_path):
		print "Error: no default config file %s found!" % defaults_filename
	else:
		config_files += (defaults_path, )

	config_path = config.get_config_file(config_filename)
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
	for secname, section in defaults.iteritems():
		for key, default in section.iteritems():
			value = parser.get(secname, key)
			if isinstance(default, (tuple, list)):
				if not value:
					retval = ()
				else:
					retval = [p.strip() for p in value.split(sep) if p]
			elif isinstance(default, int):
				retval = type(default)(value)
			else:
				retval = str(value)
			defaults[secname][key] = retval

	return defaults

