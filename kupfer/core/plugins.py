import pkgutil
import sys

from kupfer import pretty
from kupfer.core import settings
# import kupfer.icons on demand later

sources_attribute = "__kupfer_sources__"
text_sources_attribute = "__kupfer_text_sources__"
content_decorators_attribute = "__kupfer_contents__"
action_decorators_attribute = "__kupfer_actions__"
action_generators_attribute = "__kupfer_action_generators__"
settings_attribute = "__kupfer_settings__"

initialize_attribute = "initialize_plugin"
finalize_attribute = "finalize_plugin"

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
        except ImportError as e:
            pretty.print_error(__name__, "import plugin '%s':" % plugin_name, e)
            continue
        except Exception as e:
            pretty.print_error(__name__, "Could not load '%s'" % plugin_name)
            pretty.print_exc(__name__)
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
            "description": desc or "",
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
        description = ("\n" + " "*left_margin).join(wrapped)
        desc.append("  %s %s %s" %
            (
                rec["name"].ljust(idlen),
                rec["version"].ljust(verlen),
                description,
            ))
    return "\n".join(desc)

_imported_plugins = {}
_plugin_hooks = {}

class LoadingError(ImportError):
    pass

def _truncate_source(text, find_attributes):
    found_info_attributes = set(find_attributes)
    lines = []
    for line in text.splitlines():
        lines.append(line)
        if not line.strip():
            continue
        first_word, *_rest = line.split(None, 1)
        if first_word in found_info_attributes:
            found_info_attributes.discard(first_word)
        if first_word in ("from", "import", "class", "def", "if"):
            raise LoadingError(("Could not pre-load plugin: Fields missing: %r. "
                "These fields need to be defined before any other code, including imports.")
                    % (list(found_info_attributes), ))
        if not found_info_attributes:
            break
    return "\n".join(lines)

def _import_plugin_fake(modpath, error=None):
    """
    Return an object that has the plugin info attributes we can rescue
    from a plugin raising on import.

    @error: If applicable, a tuple of exception info
    """
    loader = pkgutil.get_loader(modpath)
    if not loader:
        return None

    code = loader.get_source(modpath)
    if not code:
        return None

    try:
        filename = loader.get_filename(modpath)
    except AttributeError:
        try:
            filename = loader.archive + loader.prefix
        except AttributeError:
            filename = "<%s>" % modpath

    env = {
        "__name__": modpath,
        "__file__": filename,
        "__builtins__": {"_": _}
    }
    code = _truncate_source(code, info_attributes)
    try:
        eval(compile(code, filename, "exec"), env)
    except Exception as exc:
        pretty.print_error(__name__, "When loading", modpath)
        pretty.print_exc(__name__)
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
    except ImportError as exc:
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
    except Exception:
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
    except ImportError as e:
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
    except ImportError as e:
        pretty.print_info(__name__, "Skipping plugin %s: %s" % (plugin_name, e))
        return
    for attr in attrs:
        try:
            obj = getattr(plugin, attr)
        except AttributeError as e:
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
icons = None

def _load_icons(plugin_name):
    global icons
    if icons is None:
        from kupfer import icons

    try:
        _loader = _staged_import(plugin_name, _loader_hook)
    except ImportError as exc:
        return
    modname = ".".join(_plugin_path(plugin_name))

    try:
        icon_file = pkgutil.get_data(modname, PLUGIN_ICON_FILE)
    except IOError as exc:
        # icon-list file just missing, let is pass silently
        return

    def get_icon_data(basename):
        return pkgutil.get_data(modname, basename)
    icons.parse_load_icon_list(icon_file, get_icon_data, plugin_name)

def initialize_plugin(plugin_name):
    """Initialize plugin.
    Find settings attribute if defined, and initialize it
    """
    _load_icons(plugin_name)
    settings_dict = get_plugin_attribute(plugin_name, settings_attribute)
    if settings_dict:
        settings_dict.initialize(plugin_name)
    initialize = get_plugin_attribute(plugin_name, initialize_attribute)
    if initialize:
        initialize(plugin_name)
    finalize = get_plugin_attribute(plugin_name, finalize_attribute)
    if finalize:
        register_plugin_unimport_hook(plugin_name, finalize, plugin_name)

def unimport_plugin(plugin_name):
    """Remove @plugin_name from the plugin list and dereference its
    python modules.
    """
    # Run unimport hooks
    if plugin_name in _plugin_hooks:
        try:
            for callback, args in reversed(_plugin_hooks[plugin_name]):
                callback(*args)
        except:
            pretty.print_error(__name__, "Error finalizing", plugin_name)
            pretty.print_exc(__name__)
        del _plugin_hooks[plugin_name]
    del _imported_plugins[plugin_name]
    plugin_module_name = ".".join(_plugin_path(plugin_name))
    pretty.print_debug(__name__, "Dereferencing module", plugin_module_name)
    if plugin_module_name in sys.modules:
        sys.modules.pop(plugin_module_name)
    for mod in list(sys.modules):
        if mod.startswith(plugin_module_name + "."):
            pretty.print_debug(__name__, "Dereferencing module", mod)
            sys.modules.pop(mod)

def register_plugin_unimport_hook(plugin_name, callback, *args):
    if plugin_name not in _imported_plugins:
        raise ValueError("No such plugin %s" % plugin_name)
    _plugin_hooks.setdefault(plugin_name, []).append((callback, args))

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

