import contextlib

from kupfer import pretty

from kupfer.core import plugins
from kupfer.core.plugins import (load_plugin_sources, sources_attribute,
        action_decorators_attribute, text_sources_attribute,
        content_decorators_attribute, action_generators_attribute,
        initialize_plugin)

class PluginDescription (object):
    text_sources = ()
    action_decorators = ()
    content_decorators = ()
    action_generators = ()
    sources = ()

def load_plugin(plugin_id):
    """
    @S_sources are to be included directly in the catalog,
    @s_souces as just as subitems
    """
    sources = []
    text_sources = []
    action_decorators = []
    content_decorators = []
    action_generators = []

    item = plugin_id

    initialize_plugin(item)
    if not plugins.is_plugin_loaded(item):
        return PluginDescription()
    text_sources.extend(load_plugin_sources(item, text_sources_attribute))
    action_decorators.extend(load_plugin_sources(item,
        action_decorators_attribute))
    action_generators.extend(load_plugin_sources(item,
        action_generators_attribute))

    # Register all Sources as (potential) content decorators
    content_decorators.extend(load_plugin_sources(item,
        sources_attribute, instantiate=False))
    content_decorators.extend(load_plugin_sources(item,
        content_decorators_attribute, instantiate=False))
    sources.extend(load_plugin_sources(item))

    desc = PluginDescription()

    desc.text_sources = text_sources
    desc.action_decorators = action_decorators
    desc.content_decorators = content_decorators
    desc.sources = sources
    desc.action_generators = action_generators
    return desc

@contextlib.contextmanager
def exception_guard(name, callback=None, *args, **kwargs):
    "Guard for exceptions, print traceback and call @callback if any is raised"
    try:
        yield
    except Exception:
        import traceback
        pretty.print_error(__name__, "Loading %s raised an exception:" % name)
        traceback.print_exc()
        pretty.print_error(__name__, "This error is probably a bug in", name)
        pretty.print_error(__name__, "Please file a bug report")
        if callback is not None:
            callback(*args, **kwargs)

def remove_plugin(plugin_id):
    plugins.unimport_plugin(plugin_id)
