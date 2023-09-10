"""
Base kupfer objects definitions.

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import time
import typing as ty

from gi.repository import GdkPixbuf

from kupfer import icons
from kupfer.support import itertools, kupferstring, pretty
from kupfer.core import commandexec

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__all__ = [
    "KupferObject",
    "Leaf",
    "Action",
    "Source",
    "TextSource",
    "AnySource",
    "ActionGenerator",
    "_NonpersistentToken",
]


class KupferObject:
    """Base class for kupfer data model

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

    rank_adjust: int = 0
    fallback_icon_name: str = "kupfer-object"
    # _is_builtin: bool = False

    def __init__(self, name: str | None = None) -> None:
        """Init kupfer object with."""
        self.name: str = name or self.__class__.__name__
        folded_name = kupferstring.tofolded(self.name)
        self.kupfer_add_alias(folded_name)

    def kupfer_add_alias(self, alias: str) -> None:
        """Add alias to object. This create name_aliases set if not exist
        for this leaf."""
        if alias != str(self):
            if not hasattr(self, "name_aliases"):
                self.name_aliases = set()

            self.name_aliases.add(alias)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        if cached := getattr(self, "_cached_repr", None):
            return ty.cast(str, cached)

        if key := self.repr_key():
            rep = f"<{self.__module__}.{self.__class__.__name__} {key}>"
        else:
            rep = f"<{self.__module__}.{self.__class__.__name__}>"

        setattr(self, "_cached_repr", rep)
        return rep

    def repr_key(self) -> ty.Any:
        """Return an object whose str() will be used in the __repr__,
        self is returned by default.  This value is used to recognize objects,
        for example learning commonly used objects."""
        return self

    def get_description(self) -> str | None:
        """Return a description of the specific item."""
        return None

    def get_thumbnail(self, width: int, height: int) -> GdkPixbuf.Pixbuf | None:
        """Return pixbuf of size @width x @height if available.
        Most objects will not implement this."""
        return None

    def get_pixbuf(self, icon_size: int) -> GdkPixbuf.Pixbuf | None:
        """Returns an icon in pixbuf format with dimension @icon_size.

        Subclasses should implement: get_gicon and get_icon_name,
        if they make sense.  The methods are tried in that order."""

        if gicon := self.get_gicon():
            if pbuf := icons.get_icon_for_gicon(gicon, icon_size):
                return pbuf

        if icon_name := self.get_icon_name():
            if icon := icons.get_icon_for_name(icon_name, icon_size):
                return icon

        return icons.get_icon_for_name(self.fallback_icon_name, icon_size)

    def get_icon(self) -> icons.GIcon | None:
        """Returns an icon in GIcon format.

        Subclasses should implement: get_gicon and get_icon_name,
        if they make sense. The methods are tried in that order."""

        if gicon := self.get_gicon():
            if icons.is_good_gicon(gicon):
                return gicon

        if icon_name := self.get_icon_name():
            if icons.get_good_name_for_icon_names((icon_name,)):
                return icons.get_gicon_for_names(icon_name)

        return icons.get_gicon_for_names(self.fallback_icon_name)

    def get_gicon(self) -> icons.GIcon | None:
        """Return GIcon, if there is one"""
        return None

    def get_icon_name(self) -> str:
        """Return icon name. All items should have at least a generic icon name
        to return."""
        return self.fallback_icon_name


T = ty.TypeVar("T")


class _NonpersistentToken(ty.Generic[T]):
    """Hold data that goes None when pickled."""

    __slots__ = ("object",)

    def __init__(self, object_: T) -> None:
        self.object: T = object_

    def __bool__(self) -> bool:
        return bool(self.object)

    def __reduce__(self):
        return (sum, ((), None))


class Leaf(KupferObject):
    """Base class for objects

    Leaf.object is the represented object (data)
    All Leaves should be hashable (__hash__ and __eq__)
    """

    def __init__(self, obj: ty.Any, name: str) -> None:
        """Represented object @obj and its @name"""
        super().__init__(name)
        self.object = obj
        self._content_source: _NonpersistentToken[Source] | None = None

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: ty.Any) -> bool:
        return type(self) is type(other) and self.object == other.object

    def add_content(self, content: Source | None) -> None:
        """Register content source @content with Leaf"""
        if content:
            self._content_source = _NonpersistentToken(content)

    def has_content(self) -> bool:
        return bool(self._content_source)

    def content_source(self, alternate: bool = False) -> Source | None:
        """Content of leaf. it MAY alter behavior with @alternate,
        as easter egg/extra mode"""
        if self._content_source:
            return self._content_source.object

        return None

    def get_actions(self) -> ty.Iterable[Action]:
        """Default (builtin) actions for this Leaf"""
        return ()


class Action(KupferObject):
    '''Base class for all actions.

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

    fallback_icon_name: str = "kupfer-execute"
    action_accelerator: str | None = None

    def __hash__(self) -> int:
        return hash(repr(self))

    def __eq__(self, other: ty.Any) -> bool:
        return (
            type(self) is type(other)
            and repr(self) == repr(other)
            and str(self) == str(other)
        )

    def repr_key(self) -> ty.Any:
        """by default, actions of one type are all the same"""
        return None

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        """Use this action with @obj and @iobj

        leaf: the direct object (Leaf)
        iobj: the indirect object (Leaf), if ``self.requires_object``
              returns ``False``
        ctx:  optional ExecutionToken

        if ``self.wants_context`` returns ``True``, then the action
        also receives an execution context object as ``ctx``.

        Also, ``activate_multiple(self, objects, iobjects=None, ctx=None)``
        is called if it is defined and the action gets either
        multiple objects or iobjects.
        """
        raise NotImplementedError

    def wants_context(self) -> bool:
        """Return ``True`` if ``activate`` should receive the
        ActionExecutionContext as the keyword argument context

        Defaults to ``False`` in accordance with the old protocol
        """
        return False

    def is_factory(self) -> bool:
        """Return whether action may return a result collection as a Source"""
        return False

    def has_result(self) -> bool:
        """Return whether action may return a result item as a Leaf"""
        return False

    def is_async(self) -> bool:
        """If this action runs asynchronously, return True.

        Then activate(..) must return an object from the kupfer.task module,
        which will be queued to run by Kupfer's task scheduler.
        """
        return False

    def item_types(self) -> ty.Iterable[ty.Type[Leaf]]:
        """Yield types this action may apply to. This is used only
        when this action is specified in __kupfer_actions__ to "decorate"
        """
        return ()

    def valid_for_item(self, leaf: Leaf) -> bool:
        """Whether action can be used with exactly @item"""
        return True

    def requires_object(self) -> bool:
        """If this action requires a secondary object to complete is action,
        return True."""
        return False

    def object_source(self, for_item: Leaf | None = None) -> Source | None:
        """Source to use for object or None, to use the catalog (flat and
        filtered for @object_types)."""
        return None

    def object_source_and_catalog(self, for_item: Leaf) -> bool:
        return False

    def object_types(self) -> ty.Iterable[ty.Type[Leaf]]:
        """Yield types this action may use as indirect objects, if the action
        requrires it."""
        return ()


class Source(KupferObject, pretty.OutputMixin):
    """Source: Data provider for a kupfer browser.

    All Sources should be hashable and treated as equal if
    their @repr are equal!

    *source_user_reloadable*
        if True source get "Reload" action without debug mode.

    *source_prefer_sublevel*
        if True, the source by default exports its contents in a subcatalog, not
        to the toplevel.  NOTE: *Almost never* use this: let the user decide,
        default to toplevel.

    *source_use_cache*
        if True, the source can be pickled to disk to save its
        cached items until the next time the launcher is started.

    *source_scan_interval*
        set typical rescan interval (not guaranteed) in seconds.
        Set 0 to use default. values lower than min_rescan_interval in
        PeriodicRescanner are ignored.

    *rank_adjust*
        change all leaves rank by given value. This only apply to search with
        key when given leaf already pass minimum rank level.
    """

    fallback_icon_name = "kupfer-object-multiple"
    source_user_reloadable = False
    source_prefer_sublevel = False
    source_use_cache = True
    source_scan_interval: int = 0

    def __init__(self, name):
        KupferObject.__init__(self, name)
        self.cached_items: ty.Iterable[Leaf] | None = None
        self._version: int = 1
        # last source rescan timestamp
        self.last_scan: int = 0

    @property
    def version(self) -> int:
        """Version is for pickling (save and restore from cache),
        subclasses should increase self._version when changing."""
        return self._version

    def __eq__(self, other):
        return (
            type(self) is type(other)
            and repr(self) == repr(other)
            and self.version == other.version
        )

    def __hash__(self) -> int:
        return hash(repr(self))

    def toplevel_source(self) -> Source:
        return self

    def initialize(self) -> None:
        """Called when a Source enters Kupfer's system for real.

        This method is called at least once for any "real" Source. A Source
        must be able to return an icon name for get_icon_name as well as a
        description for get_description, even if this method was never called.
        """

    def finalize(self) -> None:
        """Called before a source is deactivated."""

    def repr_key(self) -> ty.Any:
        return None

    def get_items(self) -> ty.Iterable[Leaf]:
        """Internal method to compute and return the needed items.

        Subclasses should use this method to return a sequence or
        iterator to the leaves it contains
        """
        return []

    def get_items_forced(self) -> ty.Iterable[Leaf]:
        """Force compute and return items for source.
        Default - call get_items method."""
        return self.get_items()

    def is_dynamic(self) -> bool:
        """Whether to recompute contents each time it is accessed."""
        return False

    def mark_for_update(self, postpone: bool = False) -> None:
        """Mark source as changed.

        When postpone is True, cached items are not cleaned so be available to
        use and refreshed on next PeriodicRescanner run.

        If there is no cached_items source load items on next use.
        """
        self.last_scan = 0
        if not postpone:
            self.cached_items = None

    def should_sort_lexically(self) -> bool:
        """Sources should return items by most relevant order (most relevant
        first). If this is True, Source will sort items from get_item()
        in locale lexical order."""
        return False

    def get_leaves(self, force_update: bool = False) -> ty.Iterable[Leaf]:
        """Return a list of leaves.

        Subclasses should implement ``get_items()``, so that ``Source`` can
        handle sorting and caching.

        If *force_update*, ignore cache, load *all* leaves from source and store
        it into cache. Print number of items loaded.

        If source ``get_items()`` return list or tuple - also all leaves are
        loaded and stored in cache.

        Otherwise (when ``get_items()`` is generator) leaves are loaded on
        request and cached in ``SavedIterable``.

        If ``should_sort_lexically()`` is True - all leaves are loaded, sorted
        and cached.
        """

        if self.is_dynamic():
            items = (
                self.get_items_forced() if force_update else self.get_items()
            )

            if self.should_sort_lexically():
                items = kupferstring.locale_sort(items)

            return items

        if self.cached_items is None or force_update:
            items = (
                self.get_items_forced() if force_update else self.get_items()
            )
            if self.should_sort_lexically():
                # sorting make list
                items = kupferstring.locale_sort(items)

            if force_update:
                # make list when needed
                self.cached_items = itertools.as_list(items)
                self.output_debug(f"Loaded {len(self.cached_items)} items")
            elif isinstance(items, (list, tuple)):
                self.cached_items = items
                self.output_debug(f"Loaded {len(items)} items (l)")
            else:
                # use savediterable only for iterators
                self.cached_items = itertools.SavedIterable(items)
                self.output_debug("Loaded items")

            self.last_scan = int(time.time())

        return self.cached_items or ()

    def has_parent(self) -> bool:
        """Return True when source has other, parent Source."""
        return False

    def get_parent(self) -> Source | None:
        """Return parent Source for given source if exists or None."""
        return None

    def get_leaf_repr(self) -> Leaf | None:
        """Return, if appicable, another object to take the source's place as
        Leaf"""
        return None

    def get_valid_leaf_repr(self) -> tuple[bool, Leaf | None]:
        """Return, if appicable, another object to take the source's place as
        Leaf.  Return tuple (leaf representation is valid, leaf).
        Valid representation may be None, so first element of tuple must be
        checked."""
        if leaf_repr := self.get_leaf_repr():
            if hasattr(leaf_repr, "is_valid"):
                if not leaf_repr.is_valid():
                    return False, None

        return True, leaf_repr

    def provides(self) -> ty.Iterable[ty.Type[Leaf]]:
        """A seq of the types of items it provides; empty is taken as anything
        -- however most sources should set this to exactly the type they yield.
        """
        return ()

    def get_search_text(self) -> str:
        """Message displayed on gui when no item is selected."""
        return _("Type to search")

    def get_empty_text(self) -> str:
        """Text displayed when no leaves found in source."""
        return _("%s is empty") % str(self)


class TextSource(KupferObject):
    """TextSource base class implementation, this is a pseudo Source."""

    def __init__(
        self,
        name: str | None = None,
        placeholder: str | None = None,
    ) -> None:
        """
        *name*:         Localized name
        *placeholder*:  Localized placeholder when it has no input
        """
        if not name:
            name = _("Text")

        KupferObject.__init__(self, name)
        self.placeholder = placeholder

    def __eq__(self, other: ty.Any) -> bool:
        return type(self) is type(other) and repr(self).__eq__(repr(other))

    def __hash__(self) -> int:
        return hash(repr(self))

    def initialize(self) -> None:
        pass

    def repr_key(self) -> ty.Any:
        return None

    def get_rank(self) -> int:
        """All items are given this rank."""
        return 20

    def get_items(self, text: str) -> ty.Iterable[Leaf]:
        return ()

    def get_text_items(self, text: str) -> ty.Iterable[Leaf]:
        """Get leaves for string `text`."""
        return self.get_items(text)

    def has_parent(self) -> bool:
        return False

    def provides(self) -> ty.Iterable[ty.Type[Leaf]]:
        """A seq of the types of items it provides"""
        yield Leaf

    def get_icon_name(self) -> str:
        return "edit-select-all"

    def get_search_text(self) -> str:
        return self.placeholder or _("Text")

    def get_empty_text(self) -> str:
        return self.placeholder or _("Text")


# pylint: disable=too-few-public-methods
class ActionGenerator:
    """A "source" for actions.

    NOTE: The ActionGenerator should not perform any expensive
    computation, and not access any slow media (files, network) when
    returning actions.  Such expensive checks must be performed in
    each Action's valid_for_item method.
    """

    def get_actions_for_leaf(self, leaf: Leaf) -> ty.Iterable[Action]:
        """Return actions appropriate for given leaf."""
        return ()


AnySource = ty.Union[Source, TextSource]
