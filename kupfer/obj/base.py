from kupfer import datatools
from kupfer import icons
from kupfer import pretty
from kupfer.utils import locale_sort
from kupfer.kupferstring import tounicode, tofolded

__all__ = [
    "Error", "InvalidDataError", "OperationError", "InvalidLeafError",
    "KupferObject", "Leaf", "Action", "Source", "TextSource",
]

# If no gettext function is loaded at this point, we load a substitute,
# so that testing code can still work
import builtins
if not hasattr(builtins, "_"):
    def identity(x): return x
    builtins._ = identity

class Error (Exception):
    pass

class InvalidDataError (Error):
    "The data is wrong for the given Leaf"

class OperationError (Error):
    "Command execution experienced an error"

class InvalidLeafError (OperationError):
    "The Leaf passed to an Action is invalid"

_builtin_modules = frozenset([
    "kupfer.obj.objects",
    "kupfer.obj.base",
    "kupfer.obj.sources",
    "kupfer.obj.fileactions",
])

class _BuiltinObject (type):
    def __new__(mcls, name, bases, dict):
        dict["_is_builtin"] = dict["__module__"] in _builtin_modules
        return type.__new__(mcls, name, bases, dict)


class KupferObject (object, metaclass=_BuiltinObject):
    """
    Base class for kupfer data model

    This class provides a way to get at an object's:

    * icon with get_thumbnail, get_pixbuf and get_icon
    * name with unicode() or str()
    * description with get_description

    @rank_adjust should be used _very_ sparingly:
        Default actions should have +5 or +1
        Destructive (dangerous) actions should have -5 or -10

    @fallback_icon_name is a class attribute for the last fallback
    icon; it must always be accessible.
    """
    rank_adjust = 0
    fallback_icon_name = "kupfer-object"
    def __init__(self, name=None):
        """ Init kupfer object with, where
        @name *should* be a unicode object but *may* be
        a UTF-8 encoded `str`
        """
        if not name:
            name = self.__class__.__name__
        self.name = tounicode(name)
        folded_name = tofolded(self.name)
        self.kupfer_add_alias(folded_name)

    def kupfer_add_alias(self, alias):
        if alias != str(self):
            if not hasattr(self, "name_aliases"):
                self.name_aliases = set()
            self.name_aliases.add(alias)

    def __str__(self):
        return self.name

    def __repr__(self):
        key = self.repr_key()
        keys = " %s" % (key, ) if (key is not None and key != "") else ""
        if self._is_builtin:
            return "<builtin.%s%s>" % (self.__class__.__name__, keys)
        return "<%s.%s%s>" % (self.__module__, self.__class__.__name__, keys)

    def repr_key(self):
        """
        Return an object whose str() will be used in the __repr__,
        self is returned by default.
        This value is used to recognize objects, for example learning commonly
        used objects.
        """
        return self

    def get_description(self):
        """Return a description of the specific item
        which *should* be a unicode object
        """
        return None

    def get_thumbnail(self, width, height):
        """Return pixbuf of size @width x @height if available
        Most objects will not implement this
        """
        return None

    def get_pixbuf(self, icon_size):
        """
        Returns an icon in pixbuf format with dimension @icon_size

        Subclasses should implement: get_gicon and get_icon_name,
        if they make sense.
        The methods are tried in that order.
        """
        gicon = self.get_gicon()
        pbuf = gicon and icons.get_icon_for_gicon(gicon, icon_size)
        if pbuf:
            return pbuf
        icon_name = self.get_icon_name()
        icon = icon_name and icons.get_icon_for_name(icon_name, icon_size)
        if icon:
            return icon
        return icons.get_icon_for_name(self.fallback_icon_name, icon_size)

    def get_icon(self):
        """
        Returns an icon in GIcon format

        Subclasses should implement: get_gicon and get_icon_name,
        if they make sense.
        The methods are tried in that order.
        """
        gicon = self.get_gicon()
        if gicon and icons.is_good(gicon):
            return gicon
        icon_name = self.get_icon_name()
        if icon_name and icons.get_good_name_for_icon_names((icon_name, )):
            return icons.get_gicon_for_names(icon_name)
        return icons.get_gicon_for_names(self.fallback_icon_name)

    def get_gicon(self):
        """Return GIcon, if there is one"""
        return None

    def get_icon_name(self):
        """Return icon name. All items should have at least
        a generic icon name to return.
        """
        return self.fallback_icon_name

def aslist(seq):
    """Return a list out of @seq, or seq if it is a list"""
    if not isinstance(seq, type([])) and not isinstance(seq, type(())):
        seq = list(seq)
    return seq

class _NonpersistentToken (object):
    "Goes None when pickled"
    __slots__ = "object"
    def __init__(self, object_):
        self.object = object_
    def __bool__(self):
        return bool(self.object)
    def __reduce__(self):
        return (sum, ((), None))

class Leaf (KupferObject):
    """
    Base class for objects

    Leaf.object is the represented object (data)
    All Leaves should be hashable (__hash__ and __eq__)
    """
    def __init__(self, obj, name):
        """Represented object @obj and its @name"""
        super(Leaf, self).__init__(name)
        self.object = obj
        self._content_source = None

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return (type(self) == type(other) and self.object == other.object)

    def add_content(self, content):
        """Register content source @content with Leaf"""
        self._content_source = content and _NonpersistentToken(content)

    def has_content(self):
        return self._content_source

    def content_source(self, alternate=False):
        """Content of leaf. it MAY alter behavior with @alternate,
        as easter egg/extra mode"""
        return self._content_source and self._content_source.object

    def get_actions(self):
        """Default (builtin) actions for this Leaf"""
        return ()

class Action (KupferObject):
    '''
    Base class for all actions

    Implicit interface:
      valid_object will be called once for each (secondary) object
      to see if it applies. If it is not defined, all objects are
      assumed ok (within the other type/source constraints)

    def valid_object(self, obj, for_item):
        """Whether @obj is good for secondary obj,
        where @for_item is passed in as a hint for
        which it should be applied to
        """
        return True

    @action_accelerator: str or None
        Default single lowercase letter key to use for selecting the action
        quickly
    '''
    fallback_icon_name = "kupfer-execute"
    action_accelerator = None

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return (type(self) == type(other) and repr(self) == repr(other) and
                str(self) == str(other))

    def repr_key(self):
        """by default, actions of one type are all the same"""
        return ""

    def activate(self, obj, iobj=None, ctx=None):
        """Use this action with @obj and @iobj

        @obj:  the direct object (Leaf)
        @iobj: the indirect object (Leaf), if ``self.requires_object``
               returns ``False``

        if ``self.wants_context`` returns ``True``, then the action
        also receives an execution context object as ``ctx``.

        Also, ``activate_multiple(self, objects, iobjects=None, ctx=None)``
        is called if it is defined and the action gets either
        multiple objects or iobjects.
        """
        pass

    def wants_context(self):
        """Return ``True`` if ``activate`` should receive the
        ActionExecutionContext as the keyword argument context

        Defaults to ``False`` in accordance with the old protocol
        """
        return False

    def is_factory(self):
        """Return whether action may return a result collection as a Source"""
        return False

    def has_result(self):
        """Return whether action may return a result item as a Leaf"""
        return False

    def is_async(self):
        """If this action runs asynchronously, return True.

        Then activate(..) must return an object from the kupfer.task module,
        which will be queued to run by Kupfer's task scheduler.
        """
        return False

    def item_types(self):
        """Yield types this action may apply to. This is used only
        when this action is specified in __kupfer_actions__ to "decorate"
        """
        return ()

    def valid_for_item(self, item):
        """Whether action can be used with exactly @item"""
        return True

    def requires_object(self):
        """If this action requires a secondary object
        to complete is action, return True
        """
        return False

    def object_source(self, for_item=None):
        """Source to use for object or None,
        to use the catalog (flat and filtered for @object_types)
        """
        return None

    def object_source_and_catalog(self, for_item):
        return False

    def object_types(self):
        """Yield types this action may use as indirect objects, if the action
        requrires it.
        """
        return ()

class Source (KupferObject, pretty.OutputMixin):
    """
    Source: Data provider for a kupfer browser

    All Sources should be hashable and treated as equal if
    their @repr are equal!

    @source_user_reloadable if True source get "Reload" action without
        debug mode.
    @source_prefer_sublevel if True, the source by default exports
        its contents in a subcatalog, not to the toplevel.
        NOTE: *Almost never* use this: let the user decide, default to toplevel.
    @source_use_cache if True, the source can be pickled to disk to save its
        cached items until the next time the launcher is started.
    """
    fallback_icon_name = "kupfer-object-multiple"
    source_user_reloadable = False
    source_prefer_sublevel = False
    source_use_cache = True

    def __init__(self, name):
        KupferObject.__init__(self, name)
        self.cached_items = None
        self._version = 1

    @property
    def version(self):
        """version is for pickling (save and restore from cache),
        subclasses should increase self._version when changing"""
        return self._version

    def __eq__(self, other):
        return (type(self) == type(other) and repr(self) == repr(other) and
                self.version == other.version)

    def __hash__(self ):
        return hash(repr(self))

    def toplevel_source(self):
        return self

    def initialize(self):
        """
        Called when a Source enters Kupfer's system for real

        This method is called at least once for any "real" Source. A Source
        must be able to return an icon name for get_icon_name as well as a
        description for get_description, even if this method was never called.
        """
        pass

    def finalize(self):
        """
        Called before a source is deactivated.
        """
        pass

    def repr_key(self):
        return ""

    def get_items(self):
        """
        Internal method to compute and return the needed items

        Subclasses should use this method to return a sequence or
        iterator to the leaves it contains
        """
        return []

    def get_items_forced(self):
        """
        Force compute and return items for source.
        Default - call get_items method.
        """
        return self.get_items()

    def is_dynamic(self):
        """
        Whether to recompute contents each time it is accessed
        """
        return False

    def mark_for_update(self):
        """
        Mark source as changed

        it should be reloaded on next used (if normally cached)
        """
        self.cached_items = None

    def should_sort_lexically(self):
        """
        Sources should return items by most relevant order (most
        relevant first). If this is True, Source will sort items
        from get_item() in locale lexical order
        """
        return False

    def get_leaves(self, force_update=False):
        """
        Return a list of all leaves.

        Subclasses should implement get_items, so that Source
        can handle sorting and caching.
        if @force_update, ignore cache, print number of items loaded
        """
        if self.should_sort_lexically():
            # sort in locale order
            sort_func = locale_sort
        else:
            sort_func = lambda x: x

        if self.is_dynamic():
            if force_update:
                return sort_func(self.get_items_forced())
            else:
                return sort_func(self.get_items())

        if self.cached_items is None or force_update:
            if force_update:
                self.cached_items = aslist(sort_func(self.get_items_forced()))
                self.output_debug("Loaded %d items" % len(self.cached_items))
            else:
                self.cached_items = \
                        datatools.SavedIterable(sort_func(self.get_items()))
                self.output_debug("Loaded items")
        return self.cached_items

    def has_parent(self):
        return False

    def get_parent(self):
        return None

    def get_leaf_repr(self):
        """Return, if appicable, another object
        to take the source's place as Leaf"""
        return None

    def provides(self):
        """A seq of the types of items it provides;
        empty is taken as anything -- however most sources
        should set this to exactly the type they yield
        """
        return ()

    def get_search_text(self):
        return _("Type to search")

    def get_empty_text(self):
        return _("%s is empty") % str(self)


class TextSource (KupferObject):
    """TextSource base class implementation,

    this is a psedo Source"""
    def __init__(self, name=None, placeholder=None):
        """
        name: Localized name
        placeholder: Localized placeholder when it has no input
        """
        if not name:
            name = _("Text")
        KupferObject.__init__(self, name)
        self.placeholder = placeholder

    def __eq__(self, other):
        return (type(self) == type(other) and repr(self).__eq__(repr(other)))

    def __hash__(self ):
        return hash(repr(self))

    def initialize(self):
        pass

    def repr_key(self):
        return ""

    def get_rank(self):
        """All items are given this rank"""
        return 20

    def get_items(self, text):
        return ()

    def get_text_items(self, text):
        """Get leaves for unicode string @text"""
        return self.get_items(text)

    def has_parent(self):
        return False

    def provides(self):
        """A seq of the types of items it provides"""
        yield Leaf

    def get_icon_name(self):
        return "edit-select-all"

    def get_search_text(self):
        return self.placeholder if self.placeholder else _("Text")

    def get_empty_text(self):
        return self.placeholder if self.placeholder else _("Text")


class ActionGenerator (object):
    """A "source" for actions

    NOTE: The ActionGenerator should not perform any expensive
    computation, and not access any slow media (files, network) when
    returning actions.  Such expensive checks must be performed in
    each Action's valid_for_item method.
    """

    def get_actions_for_leaf(self, leaf):
        '''Return actions appropriate for given leaf. '''
        return []
