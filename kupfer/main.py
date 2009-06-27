_debug = False

try:
	import gettext
except ImportError:
	# Instally dummy identity function
	import __builtin__
	__builtin__._ = lambda x: x
else:
	package_name = "kupfer"
	localedir = "./locale"
	try:
		import version_subst
	except ImportError:
		pass
	else:
		package_name = version_subst.PACKAGE_NAME
		localedir = version_subst.LOCALEDIR
	gettext.install(package_name, localedir=localedir)

def get_plugins():
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
	for rec in get_plugins():
		desc.append(_("""%(name)20s %(version)4s %(description)s""") % rec)
	return "\n".join(desc)

def get_options(default_opts=""):
	usage_string = \
	_(""" Usage:
	--version       show version information
	--help          show usage help
	--debug         enable debug info

	To configure kupfer, edit
	  %(config)s

	the default config for reference is at
	  %(defaults)s

	available plugins:
	""")
	from getopt import getopt, GetoptError
	from sys import argv

	from kupfer import config

	opts = argv[1:]
	if "--debug" in opts:
		try:
			import debug
		except ImportError, e:
			print e
		global _debug
		_debug = True
		opts.remove("--debug") 

	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	conf_path = config.save_config_file(config_filename)
	defaults_path = config.get_data_file(defaults_filename)
	plugin_list = get_plugin_desc()
	usage_text = (usage_string % {
			"config": conf_path,
			"defaults": defaults_path,
			})
	usage_text += "\n"
	usage_text += plugin_list

	try:
		opts, args = getopt(opts, "", ["version", "help"])
	except GetoptError, info:
		print info
		print usage_text
		raise SystemExit

	for k, v in opts:
		if k == "--help":
			print usage_text
			raise SystemExit
		if k == "--version":
			print_version()
			print
			print_banner()
			raise SystemExit

	return None

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

def print_version():
	from . import version
	print version.PACKAGE_NAME, version.VERSION

def print_banner():
	from . import version
	var = {
		"program": version.PROGRAM_NAME, "desc": version.SHORT_DESCRIPTION,
		"website": version.WEBSITE, "copyright": version.COPYRIGHT
	}
	print _("""%(program)s: %(desc)s
	%(copyright)s
	%(website)s
	""") % var

def main():
	import sys
	from os import path

	from . import browser, data
	from . import objects, plugin

	get_options()
	print_banner()

	s_sources = []
	S_sources = []

	def dir_source(opt):
		abs = path.abspath(path.expanduser(opt))
		return objects.DirectorySource(abs)

	def file_source(opt, depth=1):
		abs = path.abspath(path.expanduser(opt))
		return objects.FileSource((abs,), depth)

	source_config = get_config()

	def import_plugin(name):
		path = ".".join(["kupfer", "plugin", name])
		plugin = __import__(path, fromlist=(name,))
		#print "Loading plugin %s" % plugin.__name__
		return plugin

	sources_attribute = "__kupfer_sources__"
	text_sources_attribute = "__kupfer_text_sources__"
	def get_plugin_attributes(plugin_name, attrs, warn=False):
		try:
			plugin = import_plugin(plugin_name)
		except ImportError, e:
			print "Skipping module %s: %s" % (plugin_name, e)
			return
		for attr in attrs:
			try:
				obj = getattr(plugin, attr)
			except AttributeError, e:
				if warn:
					print "Plugin %s: %s" % (plugin_name, e)
				yield None
			else:
				yield obj

	def load_plugin_sources(plugin_name, attr=sources_attribute):
		(sources,) = get_plugin_attributes(plugin_name, (attr,))
		if not sources:
			return
		for source in get_plugin_attributes(plugin_name, sources, warn=True):
			yield source()

	text_sources = []
	for item in source_config["Plugins"]["Catalog"]:
		s_sources.extend(load_plugin_sources(item))
		text_sources.extend(load_plugin_sources(item, text_sources_attribute))
	for item in source_config["Plugins"]["Direct"]:
		S_sources.extend(load_plugin_sources(item))
		text_sources.extend(load_plugin_sources(item, text_sources_attribute))

	dir_depth = source_config["DeepDirectories"]["Depth"]

	for item in source_config["Directories"]["Catalog"]:
		s_sources.append(dir_source(item))
	for item in source_config["DeepDirectories"]["Catalog"]:
		s_sources.append(file_source(item, dir_depth))
	for item in source_config["Directories"]["Direct"]:
		S_sources.append(dir_source(item))
	for item in source_config["DeepDirectories"]["Direct"]:
		S_sources.append(file_source(item, dir_depth))
	
	if not S_sources and not s_sources:
		print "No sources"
		raise SystemExit(1)

	if _debug:
		from . import pretty
		pretty.debug = _debug

	dc = data.DataController()
	dc.set_sources(S_sources, s_sources)
	dc.register_text_sources(text_sources)
	w = browser.WindowController()
	w.main()

