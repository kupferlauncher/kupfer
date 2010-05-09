import os
import pkgutil
import sys

from kupfer import pretty, config
from kupfer import icons
from kupfer.core import settings

sources_attribute = "__kupfer_sources__"
text_sources_attribute = "__kupfer_text_sources__"
content_decorators_attribute = "__kupfer_contents__"
action_decorators_attribute = "__kupfer_actions__"
settings_attribute = "__kupfer_settings__"
action_generators_attribute = "__kupfer_action_generators__"

info_attributes = [
		"__kupfer_name__",
		"__version__",
		"__description__",
		"__author__",
	]

class NotEnabledError (Exception):
	"Plugin may not be imported since it is not enabled"

def get_plugin_ids():
	"""Enumerate possible plugin ids;
	return a sequence of possible plugin ids, not
	guaranteed to be plugins"""
	from kupfer import plugin

	def is_plugname(plug):
		return plug != "__init__" and not plug.endswith("_support")

	for importer, modname, ispkg in pkgutil.iter_modules(plugin.__path__):
		if is_plugname(modname):
			yield modname

class FakePlugin (object):
	def __init__(self, plugin_id, attributes, exc_info):
		self.is_fake_plugin = True
		self.exc_info = exc_info
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
			plugin = import_plugin_any(plugin_name)
			if not plugin:
				continue
			plugin = vars(plugin)
		except ImportError, e:
			pretty.print_error(__name__, "import plugin '%s':" % plugin_name, e)
			continue
		localized_name = plugin.get("__kupfer_name__", None)
		desc = plugin.get("__description__", "")
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
			"description": desc or u"",
			"author": author,
			"provides": (),
		}

def get_plugin_desc():
	"""Return a formatted list of plugins suitable for printing to terminal"""
	import textwrap
	infos = list(get_plugin_info())
	verlen = max(len(r["version"]) for r in infos)
	idlen = max(len(r["name"]) for r in infos)
	maxlen = 78
	left_margin = 2 + idlen + 1 + verlen + 1
	desc = []
	for rec in infos:
		# Wrap the description and align continued lines
		wrapped = textwrap.wrap(rec["description"], maxlen - left_margin)
		description = (u"\n" + u" "*left_margin).join(wrapped)
		desc.append("  %s %s %s" %
			(
				rec["name"].ljust(idlen),
				rec["version"].ljust(verlen),
				description,
			))
	return "\n".join(desc)

_imported_plugins = {}

def _truncate_code(code, find_attributes):
	"Truncate @code where all of @find_attributes have been stored."
	import dis
	import types

	found_info_attributes = set(find_attributes)
	def _new_code(c, codestring):
		newcode = types.CodeType(c.co_argcount,
		                         c.co_nlocals,
		                         c.co_stacksize,
		                         c.co_flags,
		                         codestring,
		                         c.co_consts,
		                         c.co_names,
		                         c.co_varnames,
		                         c.co_filename,
		                         c.co_name,
		                         c.co_firstlineno,
		                         c.co_lnotab)
		return newcode

	none_index = list(code.co_consts).index(None)
	i = 0
	end = len(code.co_code)
	while i < end:
		if not found_info_attributes:
			# Insert an instruction to return [None] right here
			# then truncate the code at this point
			endinstr = [
				dis.opmap["LOAD_CONST"],
				none_index & 255,
				none_index >> 8,
				dis.opmap["RETURN_VALUE"],
			]
			c = list(code.co_code)
			c[i:] = map(chr, endinstr)
			ncode = _new_code(code, ''.join(c))
			return ncode

		op = ord(code.co_code[i])
		name = dis.opname[op]

		if op >= dis.HAVE_ARGUMENT:
			b1 = ord(code.co_code[i+1])
			b2 = ord(code.co_code[i+2])
			num = b2 * 256 + b1

			if name == 'STORE_NAME':
				global_name = code.co_names[num]
				found_info_attributes.discard(global_name)

			i += 3
		else:
			i += 1
	pretty.print_debug(__name__, "Code used until end:", code)
	return code

def _import_plugin_fake(modpath, error=None):
	"""
	Return an object that has the plugin info attributes we can rescue
	from a plugin raising on import.

	@error: If applicable, a tuple of exception info
	"""
	loader = pkgutil.get_loader(modpath)
	if not loader:
		return None

	code = loader.get_code(modpath)
	if not code:
		return None

	try:
		filename = loader.get_filename()
	except AttributeError:
		try:
			filename = loader.archive + loader.prefix
		except AttributeError:
			filename = "<%s>" % modpath

	env = {
		"__name__": modpath,
		"__file__": filename,
	}
	code = _truncate_code(code, info_attributes)
	try:
		eval(code, env)
	except Exception, exc:
		pretty.print_debug(__name__, "Loading", modpath, exc)
	attributes = dict((k, env.get(k)) for k in info_attributes)
	attributes.update((k, env.get(k)) for k in ["__name__", "__file__"])
	return FakePlugin(modpath, attributes, error)

def _import_hook_fake(pathcomps):
	modpath = ".".join(pathcomps)
	return _import_plugin_fake(modpath)

def _import_hook_true(pathcomps):
	"""@pathcomps path components to the import"""
	path = ".".join(pathcomps)
	fromlist = pathcomps[-1:]
	try:
		setctl = settings.GetSettingsController()
		if not setctl.get_plugin_enabled(pathcomps[-1]):
			raise NotEnabledError("%s is not enabled" % pathcomps[-1])
		plugin = __import__(path, fromlist=fromlist)
	except ImportError, exc:
		# Try to find a fake plugin if it exists
		plugin = _import_plugin_fake(path, error=sys.exc_info())
		if not plugin:
			raise
		pretty.print_error(__name__, "Could not import plugin '%s': %s" %
				(plugin.__name__, exc))
	else:
		pretty.print_debug(__name__, "Loading %s" % plugin.__name__)
		pretty.print_debug(__name__, "  from %s" % plugin.__file__)
	return plugin

def _import_plugin_true(name):
	"""Try to import the plugin from the package, 
	and then from our plugin directories in $DATADIR
	"""
	plugin = None
	try:
		plugin = _staged_import(name, _import_hook_true)
	except ImportError:
		# Reraise to send this up
		raise
	except NotEnabledError:
		raise
	except Exception, e:
		# catch any other error for plugins and write traceback
		import traceback
		traceback.print_exc()
		pretty.print_error(__name__, "Could not import plugin '%s'" % name)
	return plugin

def _staged_import(name, import_hook):
	"Import plugin @name using @import_hook"
	plugin = None
	try:
		plugin = import_hook(_plugin_path(name))
	except ImportError, e:
		if name not in e.args[0]:
			raise
	return plugin


def import_plugin(name):
	if is_plugin_loaded(name):
		return _imported_plugins[name]
	plugin = None
	try:
		plugin = _import_plugin_true(name)
	except NotEnabledError:
		plugin = _staged_import(name, _import_hook_fake)
	finally:
		# store nonexistant plugins as None here
		_imported_plugins[name] = plugin
	return plugin

def import_plugin_any(name):
	if name in _imported_plugins:
		return _imported_plugins[name]
	return _staged_import(name, _import_hook_fake)

def _plugin_path(name):
	return ("kupfer", "plugin", name)


# Plugin Attributes
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
			if instantiate:
				yield source()
			else:
				yield source
		else:
			pretty.print_info(__name__, "Source not found for %s" % plugin_name)


# Plugin Initialization & Error
def is_plugin_loaded(plugin_name):
	return (plugin_name in _imported_plugins and
			not getattr(_imported_plugins[plugin_name], "is_fake_plugin", None))

def _loader_hook(modpath):
	modname = ".".join(modpath)
	loader = pkgutil.find_loader(modname)
	if not loader:
		raise ImportError("No loader found for %s" % modname)
	if not loader.is_package(modname):
		raise ImportError("Is not a package")
	return loader

PLUGIN_ICON_FILE = "icon-list"

def _load_icons(plugin_name):
	try:
		loader = _staged_import(plugin_name, _loader_hook)
	except ImportError, exc:
		return
	modname = ".".join(_plugin_path(plugin_name))

	try:
		icon_file = pkgutil.get_data(modname, PLUGIN_ICON_FILE)
	except IOError, exc:
		pretty.print_debug(__name__, type(exc).__name__, exc)
		return

	for line in icon_file.splitlines():
		# ignore '#'-comments
		if line.startswith("#") or not line.strip():
			continue
		icon_name, basename = (i.strip() for i in line.split("\t", 1))
		icon_data = pkgutil.get_data(modname, basename)
		icons.load_plugin_icon(plugin_name, icon_name, icon_data)


def initialize_plugin(plugin_name):
	"""Initialize plugin.
	Find settings attribute if defined, and initialize it
	"""
	_load_icons(plugin_name)
	settings_dict = get_plugin_attribute(plugin_name, settings_attribute)
	if not settings_dict:
		return
	settings_dict.initialize(plugin_name)

def unimport_plugin(plugin_name):
	del _imported_plugins[plugin_name]
	sys.modules.pop(".".join(_plugin_path(plugin_name)))

def get_plugin_error(plugin_name):
	"""
	Return None if plugin is loaded without error, else
	return a tuple of exception information
	"""
	try:
		plugin = import_plugin(plugin_name)
		if getattr(plugin, "is_fake_plugin", None):
			return plugin.exc_info
	except ImportError:
		return sys.exc_info()

