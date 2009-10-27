import sys
from kupfer import pretty, config, settings

sources_attribute = "__kupfer_sources__"
text_sources_attribute = "__kupfer_text_sources__"
content_decorators_attribute = "__kupfer_contents__"
action_decorators_attribute = "__kupfer_actions__"
settings_attribute = "__kupfer_settings__"

info_attributes = [
		"__kupfer_name__",
		"__version__",
		"__description__",
		"__author__",
	]

def get_plugin_ids():
	"""Enumerate possible plugin ids;
	return a sequence of possible plugin ids, not
	guaranteed to be plugins"""
	import pkgutil
	import os

	from kupfer import plugin

	def is_plugname(plug):
		return plug != "__init__" and not plug.endswith("_support")

	plugin_ids = set()
	for importer, modname, ispkg in pkgutil.iter_modules(plugin.__path__):
		if is_plugname(modname):
			plugin_ids.add(modname)

	for plugin_dir in config.get_data_dirs("plugins"):
		name = lambda f: os.path.splitext(f)[0]
		try:
			plugin_ids.update(name(f) for f in os.listdir(plugin_dir)
					if is_plugname(name(f)))
		except (OSError, IOError), exc:
			pretty.print_error(__name__, exc)
	return plugin_ids

class FakePlugin (object):
	def __init__(self, plugin_id, attributes, error_message):
		self.is_fake_plugin = True
		self.error_message = error_message
		self.__name__ = plugin_id
		vars(self).update(attributes)
	def __repr__(self):
		return "<%s %s>" % (type(self).__name__, self.__name__)

def get_plugin_info():
	"""Generator, yields dictionaries of plugin descriptions

	with at least the fields:
	name
	localized_name
	version
	description
	author
	"""
	for plugin_name in sorted(get_plugin_ids()):
		try:
			plugin = import_plugin(plugin_name)
			if not plugin:
				continue
			plugin = vars(plugin)
		except ImportError, e:
			pretty.print_error(__name__, "import plugin '%s':" % plugin_name, e)
			continue
		localized_name = plugin.get("__kupfer_name__", None)
		desc = plugin.get("__description__", _("(no description)"))
		vers = plugin.get("__version__", "")
		author = plugin.get("__author__", "")
		# skip false matches;
		# all plugins have to have @localized_name
		if localized_name is None:
			continue
		yield {
			"name": plugin_name,
			"localized_name": localized_name,
			"version": vers,
			"description": desc,
			"author": author,
			"provides": (),
		}

def get_plugin_desc():
	desc = []
	for rec in get_plugin_info():
		desc.append(_("""  %(name)-20s %(version)-4s %(description)s""") % rec)
	return "\n".join(desc)

imported_plugins = {}

def import_fake_plugin(modpath):
	"""
	Return an object that has the plugin info attributes we can rescue
	from a plugin raising on import.
	"""
	import pkgutil

	loader = pkgutil.get_loader(modpath)
	if not loader:
		return None
	env = {}
	try:
		eval(loader.get_code(), env)
	except Exception, exc:
		error = unicode(exc)
	else:
		error = None
		pretty.print_error(__name__, "Fake plugin for good plugin", modpath)
	attributes = dict((k, env.get(k)) for k in info_attributes)
	return FakePlugin(modpath, attributes, error)

def import_plugin(name):
	"""Try to import the plugin from the package, 
	and then from our plugin directories in $DATADIR
	"""
	if name in imported_plugins:
		return imported_plugins[name]
	def importit(pathcomps):
		"""@pathcomps path components to the import"""
		path = ".".join(pathcomps)
		fromlist = pathcomps[-1:]
		try:
			plugin = __import__(path, fromlist=fromlist)
		except ImportError, exc:
			# Try to find a fake plugin if it exists
			plugin = import_fake_plugin(path)
			if not plugin:
				raise
			pretty.print_error(__name__, "Could not import plugin '%s': %s" %
					(plugin.__name__, exc))
		else:
			pretty.print_debug(__name__, "Loading %s" % plugin.__name__)
			pretty.print_debug(__name__, "  from %s" % plugin.__file__)
		return plugin

	plugin = None
	try:
		try:
			plugin = importit(("kupfer", "plugin", name))
		except ImportError, e:
			if name not in e.args[0]:
				raise
			oldpath = sys.path
			try:
				# Look in datadir kupfer/plugins for plugins
				# (and in current directory)
				extra_paths = list(config.get_data_dirs("plugins"))
				sys.path = extra_paths + sys.path
				plugin = importit((name,))
			finally:
				sys.path = oldpath
	except ImportError, e:
		# Reraise to send this up
		raise
	except StandardError, e:
		# catch any other error for plugins and write traceback
		import traceback
		traceback.print_exc()
		pretty.print_error(__name__, "Could not import plugin '%s'" % name)
	finally:
		# store nonexistant plugins as None here
		imported_plugins[name] = plugin
	return plugin

def get_plugin_attributes(plugin_name, attrs, warn=False):
	"""Generator of the attributes named @attrs
	to be found in plugin @plugin_name
	if the plugin is not found, we write an error
	and yield nothing.

	if @warn, we print a warning if a plugin does not have
	a requested attribute
	"""
	try:
		plugin = import_plugin(plugin_name)
	except ImportError, e:
		pretty.print_info(__name__, "Skipping plugin %s: %s" % (plugin_name, e))
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

def get_plugin_attribute(plugin_name, attr):
	"""Get single plugin attribute"""
	attrs = tuple(get_plugin_attributes(plugin_name, (attr,)))
	obj, = (attrs if attrs else (None, ))
	return obj

def load_plugin_sources(plugin_name, attr=sources_attribute, instantiate=True):
	sources = get_plugin_attribute(plugin_name, attr)
	if not sources:
		return
	for source in get_plugin_attributes(plugin_name, sources, warn=True):
		if source:
			pretty.print_debug(__name__, "Found %s.%s" % ( source.__module__,
				source.__name__))
			if instantiate:
				yield source()
			else:
				yield source
		else:
			pretty.print_info(__name__, "Source not found for %s" % plugin_name)

def initialize_plugin(plugin_name):
	"""Initialize plugin.
	Find settings attribute if defined, and initialize it
	"""
	settings_dict = get_plugin_attribute(plugin_name, settings_attribute)
	if not settings_dict:
		return
	settings_dict.initialize(plugin_name)

def get_plugin_error(plugin_name):
	"""
	Return None if plugin is loaded without error, else
	return a string describing the error.
	"""
	try:
		plugin = import_plugin(plugin_name)
		if getattr(plugin, "is_fake_plugin", None):
			return plugin.error_message
	except ImportError, e:
		return "'%s' is not a plugin" % plugin_name
