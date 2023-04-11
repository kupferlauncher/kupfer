__kupfer_name__ = "Core"
# The following attributes are updated later
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_contents__ = ()
__kupfer_actions__ = (
    "SearchInside",
    "CopyToClipboard",
    "Rescan",
)
__description__ = "Core actions and items"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import typing as ty
from contextlib import suppress

from gi.repository import Gdk, Gtk

from kupfer import interface
from kupfer.obj import Action, Leaf, SourceLeaf
from kupfer.obj.apps import AppLeaf
from kupfer.obj.exceptions import InvalidLeafError
from kupfer.obj.sources import MultiSource
from kupfer.plugin.core import commands, contents, internal, text
from kupfer.support import pretty, task

if ty.TYPE_CHECKING:
    _ = str


def _is_debug():
    # Return True if Kupfer is in debug mode
    return pretty.DEBUG


def register_subplugin(module):
    attrs = (
        "__kupfer_sources__",
        "__kupfer_actions__",
        "__kupfer_text_sources__",
        "__kupfer_contents__",
    )
    for attr in attrs:
        object_names = getattr(module, attr, ())
        globals()[attr] += object_names
        globals().update((sym, getattr(module, sym)) for sym in object_names)


register_subplugin(contents)
register_subplugin(text)
register_subplugin(internal)
register_subplugin(commands)

if _is_debug():
    from kupfer.plugin.core import debug

    register_subplugin(debug)


def initialize_plugin(x):
    # pylint: disable=import-outside-toplevel
    from kupfer.plugin.core import alternatives

    alternatives.initialize_alternatives(__name__)


class _MultiSource(MultiSource):
    def is_dynamic(self):
        return False


class SearchInside(Action):
    """Return the content source for a Leaf"""

    def __init__(self):
        super().__init__(_("Search Contents"))

    def is_factory(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        if not leaf.has_content():
            raise InvalidLeafError("Must have content")

        return leaf.content_source()

    def activate_multiple(self, objs):
        return _MultiSource([L.content_source() for L in objs])

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return leaf.has_content()

    def get_description(self):
        return _("Search inside this catalog")

    def get_icon_name(self):
        return "kupfer-search"


class CopyToClipboard(Action):
    # rank down since it applies everywhere
    rank_adjust = -2
    action_accelerator = "c"

    def __init__(self):
        Action.__init__(self, _("Copy"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        clip = Gtk.Clipboard.get_for_display(
            ctx.environment.get_screen().get_display(), Gdk.SELECTION_CLIPBOARD
        )
        interface.copy_to_clipboard(leaf, clip)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        with suppress(AttributeError):
            return bool(interface.get_text_representation(leaf))

    def get_description(self):
        return _("Copy to clipboard")

    def get_icon_name(self):
        return "edit-copy"


class RescanActionTask(task.ThreadTask):
    def __init__(self, source, async_token, retval):
        task.ThreadTask.__init__(self)
        self.source = source
        self.async_token = async_token
        self.retval = retval

    def thread_do(self):
        self.source.get_leaves(force_update=True)

    def thread_finish(self):
        self.async_token.register_late_result(self.retval)


class Rescan(Action):
    """A source action: Rescan a source!"""

    rank_adjust = -5

    def __init__(self):
        Action.__init__(self, _("Rescan"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        if not leaf.has_content():
            raise InvalidLeafError("Must have content")

        source = leaf.content_source()
        return RescanActionTask(source, ctx, leaf)

    def is_async(self):
        return True

    def get_description(self):
        return _("Force reindex of this source")

    def get_icon_name(self):
        return "view-refresh"

    def item_types(self):
        yield AppLeaf
        yield SourceLeaf

    def valid_for_item(self, leaf):
        if not leaf.has_content():
            return False

        if leaf.content_source().is_dynamic():
            return False

        return _is_debug() or leaf.content_source().source_user_reloadable
