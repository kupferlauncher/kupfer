import contextlib
import traceback
import typing as ty

from kupfer.obj.base import Action, ActionGenerator, Source, TextSource
from kupfer.support import pretty

from kupfer.core import plugins
from kupfer.core.plugins import (
    PluginAttr,
    initialize_plugin,
    load_plugin_objects,
)

__all__ = ("load_plugin", "exception_guard", "remove_plugin")


# pylint: disable=too-few-public-methods
class PluginDescription:
    text_sources: list[TextSource] = []
    action_decorators: list[Action] = []
    content_decorators: list[ty.Type[Source]] = []
    action_generators: list[ActionGenerator] = []
    sources: list[Source] = []


def load_plugin(plugin_id: str) -> PluginDescription:
    """Load plugin by `plugin_id`.

    @S_sources are to be included directly in the catalog,
    @s_souces as just as subitems
    """
    sources: list[Source] = []
    text_sources: list[TextSource] = []
    action_decorators: list[Action] = []
    content_decorators: list[ty.Type[Source]] = []
    action_generators: list[ActionGenerator] = []

    initialize_plugin(plugin_id)
    if not plugins.is_plugin_loaded(plugin_id):
        return PluginDescription()

    text_sources.extend(load_plugin_objects(plugin_id, PluginAttr.TEXT_SOURCES))
    action_decorators.extend(
        load_plugin_objects(plugin_id, PluginAttr.ACTION_DECORATORS)
    )
    action_generators.extend(
        load_plugin_objects(plugin_id, PluginAttr.ACTION_GENERATORS)
    )

    # Register all Sources as (potential) content decorators
    content_decorators.extend(
        load_plugin_objects(plugin_id, PluginAttr.SOURCES, instantiate=False)
    )
    content_decorators.extend(
        load_plugin_objects(
            plugin_id, PluginAttr.CONTENT_DECORATORS, instantiate=False
        )
    )
    sources.extend(load_plugin_objects(plugin_id, PluginAttr.SOURCES))

    desc = PluginDescription()

    desc.text_sources = text_sources
    desc.action_decorators = action_decorators
    desc.content_decorators = content_decorators
    desc.sources = sources
    desc.action_generators = action_generators
    return desc


@contextlib.contextmanager
def exception_guard(name, *args, callback=None, **kwargs):
    "Guard for exceptions, print traceback and call @callback if any is raised"
    try:
        yield
    except Exception:
        pretty.print_error(__name__, f"Loading {name} raised an exception:")
        traceback.print_exc()
        pretty.print_error(__name__, "This error is probably a bug in", name)
        pretty.print_error(__name__, "Please file a bug report")
        if callback is not None:
            callback(*args, **kwargs)


def remove_plugin(plugin_id: str) -> None:
    plugins.unimport_plugin(plugin_id)
