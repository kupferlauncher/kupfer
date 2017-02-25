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

from gi.repository import Gtk, Gdk

from kupfer.objects import Leaf, Action
from kupfer.obj.sources import MultiSource
from kupfer import objects
from kupfer.obj.base import InvalidLeafError
from kupfer import interface
from kupfer import pretty
from kupfer import task

def _is_debug():
    # Return True if Kupfer is in debug mode
    return pretty.debug

def register_subplugin(module):
    attrs = (
        "__kupfer_sources__",
        "__kupfer_actions__",
        "__kupfer_text_sources__",
        "__kupfer_contents__"
    )
    for attr in attrs:
        object_names = getattr(module, attr, ())
        globals()[attr] += object_names
        globals().update((sym, getattr(module, sym)) for sym in object_names)

from kupfer.plugin.core import contents, text, internal, commands

register_subplugin(contents)
register_subplugin(text)
register_subplugin(internal)
register_subplugin(commands)

if _is_debug():
    from kupfer.plugin.core import debug
    register_subplugin(debug)

def initialize_plugin(x):
    from kupfer.plugin.core import alternatives
    alternatives.initialize_alternatives(__name__)


class _MultiSource (MultiSource):
    def is_dynamic(self):
        return False

class SearchInside (Action):
    """Return the content source for a Leaf"""
    def __init__(self):
        super(SearchInside, self).__init__(_("Search Contents"))

    def is_factory(self):
        return True
    def activate(self, leaf):
        if not leaf.has_content():
            raise InvalidLeafError("Must have content")
        return leaf.content_source()

    def activate_multiple(self, objects):
        return _MultiSource([L.content_source() for L in objects])

    def item_types(self):
        yield Leaf
    def valid_for_item(self, leaf):
        return leaf.has_content()

    def get_description(self):
        return _("Search inside this catalog")
    def get_icon_name(self):
        return "kupfer-search"

class CopyToClipboard (Action):
    # rank down since it applies everywhere
    rank_adjust = -2
    def __init__(self):
        Action.__init__(self, _("Copy"))
    def wants_context(self):
        return True
    def activate(self, leaf, ctx):
        clip = Gtk.Clipboard.get_for_display(
                ctx.environment.get_screen().get_display(),
                Gdk.SELECTION_CLIPBOARD)
        interface.copy_to_clipboard(leaf, clip)
    def item_types(self):
        yield Leaf
    def valid_for_item(self, leaf):
        try:
            return bool(interface.get_text_representation(leaf))
        except AttributeError:
            pass
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

class Rescan (Action):
    """A source action: Rescan a source!  """
    rank_adjust = -5
    def __init__(self):
        Action.__init__(self, _("Rescan"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
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
        yield objects.AppLeaf
        yield objects.SourceLeaf

    def valid_for_item(self, item):
        if not item.has_content():
            return False
        if item.content_source().is_dynamic():
            return False
        return _is_debug() or item.content_source().source_user_reloadable
