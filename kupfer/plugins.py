from kupfer import pretty

sources_attribute = "__kupfer_sources__"
text_sources_attribute = "__kupfer_text_sources__"
action_decorators_attribute = "__kupfer_action_decorator__"

def get_config():
	import ConfigParser
	import os, sys

	from kupfer import config

	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	sep = ";"
	parser = ConfigParser.SafeConfigParser()
	default_directories = ("~/", "~/Desktop", )
	# Minimal "defaults" to define all fields
	# Read defaults defined in a defaults.cfg file
	defaults = {
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

def get_plugin_info():
	"""Generator, yields dictionaries of plugin descriptions

	with at least the fields:
	name
	version
	description
	author
	provides
	"""
	from kupfer import plugin
	import os

	def import_plugin(name):
		path = ".".join(["kupfer", "plugin", name])
		plugin = __import__(path, fromlist=(name,))
		return plugin
	plugin_dir = plugin.__path__[0]
	plugin_files = set()
	for dirpath, dirs, files in os.walk(plugin_dir):
		del dirs[:]
		for f in files:
			basename = os.path.splitext(f)[0]
			if basename != "__init__" and not basename.endswith("_support"):
				plugin_files.add(basename)

	for plugin_name in sorted(plugin_files):
		try:
			plugin = import_plugin(plugin_name).__dict__
		except ImportError, e:
			print "Error:", e
			continue
		desc = plugin.get("__description__", _("(no description)"))
		vers = plugin.get("__version__", "")
		author = plugin.get("__author__", "")
		sources = plugin.get("__kupfer_sources__", None)
		# skip "empty" plugins
		if sources is None:
			continue
		yield {
			"name": plugin_name,
			"version": vers,
			"description": desc,
			"author": author,
			"provides": sources
		}

def get_plugin_desc():
	desc = []
	for rec in get_plugin_info():
		desc.append(_("""%(name)20s %(version)4s %(description)s""") % rec)
	return "\n".join(desc)

imported_plugins = {}

def import_plugin(name):
	if name in imported_plugins:
		return imported_plugins[name]
	path = ".".join(["kupfer", "plugin", name])
	plugin = __import__(path, fromlist=(name,))
	pretty.print_debug(__name__, "Loading %s" % plugin.__name__)
	imported_plugins[name] = plugin
	return plugin

def get_plugin_attributes(plugin_name, attrs, warn=False):
	try:
		plugin = import_plugin(plugin_name)
	except ImportError, e:
		pretty.print_info(__name__, "Skipping module %s: %s" % (plugin_name, e))
		return
	for attr in attrs:
		try:
			obj = getattr(plugin, attr)
		except AttributeError, e:
			if warn:
				pretty.print_info(__name__, "Plugin %s: %s" % (plugin_name, e))
			yield None
		else:
			yield obj

def load_plugin_sources(plugin_name, attr=sources_attribute):
	(sources,) = get_plugin_attributes(plugin_name, (attr,))
	if not sources:
		return
	for source in get_plugin_attributes(plugin_name, sources, warn=True):
		pretty.print_debug(__name__, "Found %s.%s" % ( source.__module__,
			source.__name__))
		yield source()
