from __future__ import annotations

import pkgutil
import sys
import textwrap
import traceback
import types
import typing as ty
from enum import Enum

from kupfer import icons
from kupfer import plugin as kplugin
from kupfer.core import settings
from kupfer.support import pretty

if ty.TYPE_CHECKING:
    from gettext import gettext as _

    from kupfer.support.types import ExecInfo

# import kupfer.icons on demand later

__all__ = (
    "LoadingError",
    "NotEnabledError",
    "PluginAttr",
    "get_plugin_attribute",
    "get_plugin_attributes",
    "get_plugin_desc",
    "get_plugin_error",
    "get_plugin_ids",
    "get_plugin_info",
    "get_plugin_name",
    "initialize_plugin",
    "is_plugin_loaded",
    "load_plugin_objects",
    "register_plugin_unimport_hook",
    "unimport_plugin",
)


class PluginAttr(Enum):
    SOURCES = "__kupfer_sources__"
    TEXT_SOURCES = "__kupfer_text_sources__"
    CONTENT_DECORATORS = "__kupfer_contents__"
    ACTION_DECORATORS = "__kupfer_actions__"
    ACTION_GENERATORS = "__kupfer_action_generators__"
    SETTINGS = "__kupfer_settings__"
    INITIALIZE = "initialize_plugin"
    FINALIZE = "finalize_plugin"

    # info attributes
    KUPFER_NAME = "__kupfer_name__"
    VERSION = "__version__"
    DESCRIPTION = "__description__"
    AUTHOR = "__author__"

    # other
    NAME = "__name__"
    FILE = "__file__"


_INFO_ATTRIBUTES = tuple(
    pa.value
    for pa in (
        PluginAttr.KUPFER_NAME,
        PluginAttr.VERSION,
        PluginAttr.DESCRIPTION,
        PluginAttr.AUTHOR,
    )
)

_PLUGIN_ICON_FILE = "icon-list"
_PLUGIN_HOOKS: dict[str, list[tuple[ty.Callable[..., None], ty.Any]]] = {}


class NotEnabledError(Exception):
    """Plugin may not be imported since it is not enabled"""


def get_plugin_ids() -> ty.Iterator[str]:
    """Enumerate possible plugin ids. Return a sequence of possible plugin ids,
    not guaranteed to be plugins."""

    for _importer, modname, _ispkg in pkgutil.iter_modules(kplugin.__path__):
        if (
            modname != "__init__"
            and not modname.endswith("_support")
            and not modname.startswith("_")
        ):
            yield modname


# pylint: disable=too-few-public-methods
class _FakePlugin:
    def __init__(
        self,
        plugin_id: str,
        attributes: dict[str, ty.Any],
        exc_info: ExecInfo | None,
    ) -> None:
        self.is_fake_plugin = True
        self.exc_info = exc_info
        self.__name__ = plugin_id
        vars(self).update(attributes)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.__name__}>"


PluginModule = ty.Union[types.ModuleType, _FakePlugin]
# imported plugins, none=not existing
_IMPORTED_PLUGINS: dict[str, PluginModule | None] = {}


def get_plugin_info() -> ty.Iterator[dict[str, ty.Any]]:
    """Generator, yields dictionaries of plugin descriptions with at least the
    fields: name, localized_name, version, description, author."""
    for plugin_name in sorted(get_plugin_ids()):
        try:
            plugin = _import_plugin_any(plugin_name)
            if not plugin:
                continue

            plugin = vars(plugin)
        except ImportError as exc:
            pretty.print_error(__name__, f"import plugin '{plugin_name}':", exc)
            continue
        except Exception:
            pretty.print_error(__name__, f"Could not load '{plugin_name}'")
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


def get_plugin_desc() -> str:
    """Return a formatted list of plugins suitable for printing to terminal"""
    infos = list(get_plugin_info())
    verlen = max(len(r["version"]) for r in infos)
    idlen = max(len(r["name"]) for r in infos)
    maxlen = 78
    left_margin = 2 + idlen + 1 + verlen + 1

    def format_desc(rec: dict[str, ty.Any]) -> str:
        # Wrap the description and align continued lines
        wrapped = textwrap.wrap(rec["description"], maxlen - left_margin)
        description = ("\n" + " " * left_margin).join(wrapped)
        name = rec["name"].ljust(idlen)
        ver = rec["version"].ljust(verlen)
        return f"  {name} {ver} {description}"

    return "\n".join(map(format_desc, infos))


class LoadingError(ImportError):
    pass


def _truncate_source(
    text: str, find_attributes: ty.Iterable[str]
) -> ty.Iterator[str]:
    found_info_attributes = set(find_attributes)
    for line in text.splitlines():
        # skip import from __future__ that must be in first line
        if line.startswith("from __future__ import "):
            continue

        # keep empty lines
        if not line.strip():
            yield line
            continue

        first_word = line.split(None, 1)[0]
        if first_word in found_info_attributes:
            found_info_attributes.discard(first_word)
        elif first_word in ("from", "import", "class", "def", "if"):
            break

        yield line

    if found_info_attributes:
        raise LoadingError(
            "Could not pre-load plugin: Fields missing: "
            f"{list(found_info_attributes)}. "
            "These fields need to be defined before any other code, "
            "including imports."
        )


def _import_plugin_fake(
    modpath: str, error: ExecInfo | None = None
) -> _FakePlugin | None:
    """Return an object that has the plugin info attributes we can rescue
    from a plugin raising on import.

    @error: If applicable, a tuple of exception info
    """
    loader = pkgutil.get_loader(modpath)
    if not loader:
        return None

    code = loader.get_source(modpath)  # type: ignore
    if not code:
        return None

    try:
        filename = loader.get_filename(modpath)  # type: ignore
    except AttributeError:
        try:
            filename = loader.archive + loader.prefix  # type: ignore
        except AttributeError:
            filename = f"<{modpath}>"

    env = {"__name__": modpath, "__file__": filename, "__builtins__": {"_": _}}
    code = "\n".join(_truncate_source(code, _INFO_ATTRIBUTES))
    try:
        # pylint: disable=eval-used
        eval(compile(code, filename, "exec"), env)
    except Exception:
        pretty.print_error(__name__, "When loading", modpath)
        pretty.print_exc(__name__)

    attributes = {k: env.get(k) for k in _INFO_ATTRIBUTES}
    attributes.update(
        (k.value, env.get(k.value)) for k in (PluginAttr.NAME, PluginAttr.FILE)
    )
    return _FakePlugin(modpath, attributes, error)


def _import_hook_fake(pathcomps: ty.Iterable[str]) -> PluginModule | None:
    modpath = ".".join(pathcomps)
    return _import_plugin_fake(modpath)


def _import_hook_true(pathcomps: tuple[str, ...]) -> PluginModule:
    """@pathcomps path components to the import"""
    path = ".".join(pathcomps)
    fromlist = pathcomps[-1:]
    try:
        setctl = settings.get_settings_controller()
        if not setctl.get_plugin_enabled(pathcomps[-1]):
            raise NotEnabledError(f"{pathcomps[-1]} is not enabled")

        plugin = __import__(path, fromlist=fromlist)
        pretty.print_debug(__name__, f"Loading {plugin.__name__}")
        pretty.print_debug(__name__, f"  from {plugin.__file__}")
        return plugin

    except ImportError as exc:
        # Try to find a fake plugin if it exists
        fake_plugin = _import_plugin_fake(path, error=sys.exc_info())
        if not fake_plugin:
            raise

        pretty.print_error(
            __name__,
            f"Could not import plugin '{fake_plugin.__name__}': {exc}",
        )
        return fake_plugin


def _import_plugin_true(name: str) -> PluginModule | None:
    """Try to import the plugin from the package, and then from our plugin
    directories in $."""
    plugin = None
    try:
        plugin = _staged_import(name, _import_hook_true)
    except (ImportError, NotEnabledError):
        # Reraise to send this up
        raise
    except Exception:
        # catch any other error for plugins and write traceback
        traceback.print_exc()
        pretty.print_error(__name__, f"Could not import plugin '{name}'")

    return plugin


def _staged_import(
    name: str,
    import_hook: ty.Callable[[tuple[str, ...]], PluginModule | None],
) -> PluginModule | None | ty.Any:
    """Import plugin @name using @import_hook"""
    # FIXME: ty.Any because typeguard
    try:
        return import_hook(_plugin_path(name))
    except ImportError as exc:
        if name not in exc.args[0]:
            raise

    return None


def _import_plugin(name: str) -> PluginModule | None:
    if is_plugin_loaded(name):
        return _IMPORTED_PLUGINS[name]

    plugin = None
    try:
        plugin = _import_plugin_true(name)
    except NotEnabledError:
        plugin = _staged_import(name, _import_hook_fake)
    finally:
        # store non-existing plugins as None here
        _IMPORTED_PLUGINS[name] = plugin

    return plugin


def _import_plugin_any(name: str) -> ty.Any:
    if name in _IMPORTED_PLUGINS:
        return _IMPORTED_PLUGINS[name]

    return _staged_import(name, _import_hook_fake)


def _plugin_path(name: str) -> tuple[str, ...]:
    return ("kupfer", "plugin", name)


# Plugin Attributes
def get_plugin_attributes(
    plugin_name: str,
    attrs: tuple[str | PluginAttr, ...],
    warn: bool = False,
) -> ty.Iterator[ty.Any]:
    """Generator of the attributes named @attrs to be found in plugin
    @plugin_name. If the plugin is not found, we write an error and yield
    nothing. If @warn, we print a warning if a plugin does not have a requested
    attribute."""
    try:
        plugin = _import_plugin(plugin_name)
    except ImportError as exc:
        pretty.print_info(__name__, f"Skipping plugin {plugin_name}: {exc}")
        return

    for attr in attrs:
        if isinstance(attr, PluginAttr):
            attr = attr.value  # noqa: PLW2901

        try:
            yield getattr(plugin, attr)
        except AttributeError as exc:
            if warn:
                pretty.print_info(__name__, f"Plugin {plugin_name}: {exc}")

            yield None


def get_plugin_attribute(
    plugin_name: str, attr: PluginAttr | str
) -> ty.Any | None:
    """Get single plugin attribute"""
    for value in get_plugin_attributes(plugin_name, (attr,)):
        return value or None

    return None


def load_plugin_objects(
    plugin_name: str,
    attr: PluginAttr = PluginAttr.SOURCES,
    instantiate: bool = True,
) -> ty.Iterable[ty.Any]:
    """Load plugin sources or actions or other type objects (selected by @attr)."""
    objects = get_plugin_attribute(plugin_name, attr)
    if not objects:
        return

    for obj in get_plugin_attributes(plugin_name, objects, warn=True):
        if obj:
            if instantiate:
                yield obj()
            else:
                yield obj

        else:
            pretty.print_info(
                __name__, f"Object not found for {plugin_name} in {attr}"
            )


# Plugin Initialization & Error
def is_plugin_loaded(plugin_name: str) -> bool:
    if plg := _IMPORTED_PLUGINS.get(plugin_name):
        return not getattr(plg, "is_fake_plugin", None)

    return False


def _loader_hook(modpath: tuple[str, ...]) -> ty.Any:
    modname = ".".join(modpath)
    loader = pkgutil.find_loader(modname)
    if not loader:
        raise ImportError(f"No loader found for {modname}")

    if not loader.is_package(modname):  # type: ignore
        raise ImportError("Is not a package")

    return loader


def _load_icons(plugin_name: str) -> None:
    try:
        _loader = _staged_import(plugin_name, _loader_hook)
    except ImportError:
        return

    modname = ".".join(_plugin_path(plugin_name))

    try:
        icon_file = pkgutil.get_data(modname, _PLUGIN_ICON_FILE)
    except OSError:
        # icon-list file just missing, let is pass silently
        return

    def get_icon_data(basename):
        return pkgutil.get_data(modname, basename)

    if icon_file:
        icons.parse_load_icon_list(icon_file, get_icon_data, plugin_name)


def initialize_plugin(plugin_name: str) -> None:
    """Initialize plugin.  Find settings attribute if defined, and initialize
    it."""
    _load_icons(plugin_name)
    if settings_dict := get_plugin_attribute(plugin_name, PluginAttr.SETTINGS):
        settings_dict.initialize(plugin_name)

    if initialize := get_plugin_attribute(plugin_name, PluginAttr.INITIALIZE):
        initialize(plugin_name)

    if finalize := get_plugin_attribute(plugin_name, PluginAttr.FINALIZE):
        register_plugin_unimport_hook(plugin_name, finalize, plugin_name)


def unimport_plugin(plugin_name: str) -> None:
    """Remove @plugin_name from the plugin list and dereference its
    python modules."""
    # Run unimport hooks
    if plugin_name in _PLUGIN_HOOKS:
        try:
            for callback, args in reversed(_PLUGIN_HOOKS[plugin_name]):
                callback(*args)

        except Exception:
            pretty.print_error(__name__, "Error finalizing", plugin_name)
            pretty.print_exc(__name__)

        _PLUGIN_HOOKS.pop(plugin_name)

    _IMPORTED_PLUGINS.pop(plugin_name)
    plugin_module_name = ".".join(_plugin_path(plugin_name))
    pretty.print_debug(__name__, "Dereferencing module", plugin_module_name)
    if plugin_module_name in sys.modules:
        sys.modules.pop(plugin_module_name)

    for mod in list(sys.modules):
        if mod.startswith(plugin_module_name + "."):
            pretty.print_debug(__name__, "Dereferencing module", mod)
            sys.modules.pop(mod)


def register_plugin_unimport_hook(
    plugin_name: str, callback: ty.Callable[..., None], *args: ty.Any
) -> None:
    if plugin_name not in _IMPORTED_PLUGINS:
        raise ValueError(f"No such plugin {plugin_name}")

    _PLUGIN_HOOKS.setdefault(plugin_name, []).append((callback, args))


def get_plugin_error(plugin_name: str) -> ty.Any:
    """Return None if plugin is loaded without error, else return a tuple of
    exception information."""
    try:
        if (plugin := _import_plugin(plugin_name)) and getattr(
            plugin, "is_fake_plugin", None
        ):
            return plugin.exc_info

    except ImportError:
        return sys.exc_info()

    return None


def get_plugin_name(modulename: str) -> str:
    """Get plugin name according to @modulename.
    (return __kupfer_name__ in @modulename module).
    """
    name: str | None = None
    for module in _IMPORTED_PLUGINS.values():
        if not module or isinstance(module, _FakePlugin):
            continue

        if module.__name__ == modulename:
            name = module.__kupfer_name__
            break

    if name:
        return name

    return modulename.split(".")[-1]
