=================
Kupfer Plugin API
=================

.. contents:: :depth: 2


Introduction
============

Kupfer is a Python program that allows loading extension modules
at runtime. A plugin is equivalent to one Python module implemented
as one ``.py`` file or as a Python package.

The ``kupfer`` package is organized as follows::

    kupfer/
        obj/
        ui/
        core/
        plugin/
            core/__init__.py
            applications.py
            ...
        ...

Plugins live in the package ``kupfer.plugin``. Kupfer also includes
directories called ``kupfer/plugins`` from ``$XDG_DATA_DIRS``, which
typically means ``/usr/share/kupfer/plugins`` and
``$HOME/.local/share/kupfer/plugins``. These directories are
transparently included into the kupfer package, so the user has multiple
choices of where to install plugins.

The Plugin File
:::::::::::::::

A kupfer plugin is a ``.py`` file with some special attributes.

It starts like this (an imagined example)::

    __kupfer_name__ = _("Cool X-Documents")
    __kupfer_sources__ = ("DocumentSource", )
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ("Open", )
    __description__ = _("Documents from the X program")
    __version__ = "1"
    __author__ = "Tom Author"

All these special variables must be defined before any other code in the
module (even imports). For a plugin, the following attributes are
required::

    __kupfer_name__ (Localized name of plugin)
    __description__ (Localized description of plugin)
    __version__
    __author__

For the plugin to do anything, the following attributes may be defined::

    __kupfer_sources__ = ()
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ()
    __kupfer_action_generators__ = ()
    __kupfer_contents__ = ()

They should be tuples of *names* of classes in the module:

* all sources have to be subclasses of ``kupfer.objects.Source``
* all text sources have to be subclasses of ``kupfer.objects.TextSource``
* all actions have to be subclasses of ``kupfer.objects.Action``

If an example plugin declares::

    __kupfer_sources__ = ("DocumentSource", )

it will later in the file define the class ``DocumentSource``::

    from kupfer.objects import Source

    class DocumentSource (Source):
        def __init__(self):
            Source.__init__(self, _("Cool X-Documents"))

        def get_items(self):
            ...
        # later we will see what we can do here!


Ok, this looks simple. So what are Leaves, Sources and Actions?


A **Leaf** is an object, it represents a program or a file, or a text or
something else. Every type of Leaf has different possibilities, and you
can define new Leaves. Example: a ``FileLeaf`` represents a file on the
disk.

A **Source** produces a collection of Leaves, so it makes Kupfer know
about new objects. For example, it can provide all the FileLeaves for a
particular folder.

An **Action** is the part where something happens, an action is applied
to a Leaf, and something happens. For example, *Open* can be an
action that works with all ``FileLeaf``.


A Short Working Example
:::::::::::::::::::::::

The very simplest thing we can do is to provide an action on
objects that already exist in Kupfer. These actions appear in the
right-hand actions pane in kupfer, when an object of the right type is
selected.

The complete python code for the plugin:

.. code:: python

    __kupfer_name__ = _("Image Viewer")
    __kupfer_actions__ = ("View", )
    __description__ = _("View images quickly")
    __version__ = ""
    __author__ = "Tom Author"


    from gi.repository import Gtk

    from kupfer.objects import Action, FileLeaf

    class View (Action):
        def __init__(self):
            super().__init__(_("View"))

        def item_types(self):
            yield FileLeaf

        def valid_for_item(self, fileobj):
            return fileobj.object.endswith(".jpg")

        def activate(self, fileobj):
            image_widget = Gtk.Image.new_from_file(fileobj.object)
            image_widget.show()
            window = Gtk.Window()
            window.add(image_widget)
            window.present()


That is all. What we did was the following:

* Declare a plugin called "Image Viewer" with an action class ``View``.
* Every string inside ``_("")`` is translatable
* ``View`` declares that it works with ``FileLeaf``
* ``View`` only accepts ``FileLeaf`` that end with '.jpg'
* ``View`` defines a method ``activate`` that when called, will use gtk
  to show the file in a window

.. note::

    Kupfer uses a simplified programming style of composition and
    cooperative superclasses.

    You normally never call a superclass implementation inside a method
    that you define, with the exception of ``__init__``.

    On the other hand, there are superclass methods that should not be
    overridden. For example, ``KupferObject.get_pixbuf`` is never
    overridden, instead you implement ``KupferObject.get_icon_name``.


Reference
=========

Below follows a complete summary. To accompany this reference, you can
read kupfer's inline module documentation with pydoc, by doing the
following in the source directory::

    $ pydoc kupfer.obj.base

or equivalently::

    $ python
    >>> help("kupfer.obj.base")

KupferObject
::::::::::::

``class KupferObject`` implements the things that are common to all objects:
*name*, *description*, *icon*, *thumbnail* and *name aliases*.


``__init__(self, name)``
    This is called when you call ``Leaf.__init__``, or ``Source.__init__``,
    and so on in your object's ``__init__`` method.

    The name parameter must be a unicode string. An object can not
    change name after it has called __init__.

``get_description(self)``
    Return a longer user-visible unicode string that
    describes the object.

``get_icon_name(self)``
    Return a string of one icon name for the object.

    The icon name should preferably be in the `Icon Naming
    Specification`_

    .. _`Icon Naming Specification`: \
        http://standards.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html


``get_gicon(self)``
    Return a GIcon (GIO icon) object. This takes precedence
    over the icon name, if it is defined.

``get_thumbnail(self, width, height)``
    Implement ``get_thumbnail`` to return a GdkPixbuf object of the
    requested size that is a thumbnail of the object. If applicable.

``get_pixbuf(self, x)``
    This should not be redefined. Define ``get_icon_name`` and/or
    ``get_gicon`` instead.

``get_icon(self)``
    This should not be redefined. Define ``get_icon_name`` and/or
    ``get_gicon`` instead.

``repr_key(self)``
    Return an object whose str() will be used in the __repr__,
    self is returned by default.
    This value is used to differentiate and recognize objects.
    Override this if the objects type and name is not enough
    to differentiate it from other objects.

``__repr__``
    This should not be redefined. Define ``repr_key`` instead.

``kupfer_add_alias(self, alias)``
    This should not be redefined, but can be called by the object
    to add an alternate name to the object.


KupferObject Attributes
.......................

``KupferObject.rank_adjust``
    A number to adjust the ranking of a certain object. Should only
    be used on Actions. Should be set in the range -10 to -1 for actions
    that apply to many objects but not default for any.

``KupferObject.fallback_icon_name``
    Used as a the class' fallback for icon name. Do not change this.


Leaf
::::

``class Leaf`` inherits from KupferObject.

A Leaf represents an object that the user will want to act on. Examples
are a file, an application or a free-text query (TextLeaf).

This defines, in addition to KupferObject:

``__init__(self, obj, name)``
    The default implementation of ``__init__`` stores the parameter
    ``obj`` into ``self.object`` and passes ``name`` up to
    ``KupferObject.__init__``.

    ``obj`` can be any data that the Leaf represents. ``name`` must be
    a unicode string.

``Leaf.object``
    ``Leaf.object`` is the represented object, which is the
    implementation-specific internal data.

``get_actions()``
    Return a sequence of Actions that always apply to the Leaf. These
    are "built-in" actions.

``__hash__`` and ``__eq__``
    Leaves are hashable, can be members in a set, and duplicates are
    recognized (and removed); this is essential so that equivalent
    Leaves from different sources are recognized. 

    These methods need normally not be overridden.

    By default leaves are equal if both the name and the ``Leaf.object``
    attribute are the same.

``has_content()`` and ``content_source()``
    A leaf can contain something, like a folder contains files or a
    music album songs.

    If the Leaf should have content, it should override ``has_content``
    to return ``True`` and define ``content_source()`` to return
    an instance of a Source.

    A Leaf may decide dynamically if it has content or not.


Action
::::::

``class Action`` inherits from KupferObject.

An Action represents a command using a direct object and an optional
indirect object. One example is ``kupfer.obj.fileactions.Open`` that
will open its direct object (which must be a file), with its default
viewer.

Actions are the most versatile parts of Kupfer, since they can define
ways to use objects together. They also have to decide, which types of
Leaves they apply to, and if they apply to a given Leaf.

An action is either a `Subject + Verb`:t: action: It needs one object,
this is the direct object.

Or it is a `Subject + Verb + Object`:t: action: It needs two objects,
one direct object ("obj") and one indirect object ("iobj").

Action defines, in addition to KupferObject:


Activate: Carrying Out the Action
.................................

``activate(self, obj)``
    Called to perform the action if the action is a normal
    `Subject + Verb`:t: action.

``activate(self, obj, iobj)``
    Called to perform the action if the action is a three-way
    `Subject + Verb + Object`:t: action. (That is, ``requires_object``
    returns ``True``)

``activate_multiple(self, objects)``
    ..

``activate_multiple(self, objects, iobjects)``
    If implemented, ``activate_multiple`` is called with preference over
    ``activate(self, obj, iobj)`` or ``activate(self, obj)`` as
    appropriate.

    Implement ``activate_multiple`` to handle multiple objects on either
    side in a smart way.

    You should implement ``activate_multiple`` if it is possible to do
    something better than the equivalent of repeating ``activate``
    *n* times for *n* objects.

``activate`` and ``activate_multiple`` also receive a keyword argument
called ``ctx`` if the action defines ``wants_context(self)`` to return
``True``. See ``wants_context`` below for more information.


Determining Eligible Objects
............................

``item_types(self)``
    This method should return a sequence of all Leaf types
    that the action can apply to (direct object).

``valid_for_item(self, item)``
    This method is called for each potential direct object
    of the correct type.
    Return True if the object is compatible with the action.

    By default always returns ``True``.

``requires_object(self)``
    Return ``True`` if the action is a `Subject + Verb + Object`:t:
    action and requires both a direct and an indirect object.

    If ``requires_object`` returns ``True``,  then you must must also
    define (at least) ``object_types``.

``object_types(self)``
    Return a sequence of all Leaf types that are valid for the action's
    indirect object.

``object_source(self, for_item)``
    If the action's indirect objects should not be picked from the full
    catalog, but from a defined source, return an instance of the Source
    here, else return None. ``for_item`` is the direct object.

``object_source_and_catalog(self, for_item)``
    If the action has an object source, by default only that source is
    used for indirect objects. Return ``True`` here to use both the
    custom source and the whole catalog.

``valid_object(self, iobj, for_item)``
    This method, if defined,  will be called for each indirect object
    (with the direct object as ``for_item``), to decide if it can be
    used. Return ``True`` if it can be used.

Auxiliary Method ``wants_context(self)``
........................................

``wants_context(self)``
    Return ``True`` if ``activate`` should receive an ``ExecutionToken``
    as the keyword argument ``ctx``. This allows posting late
    (after-the-fact) results and errors, as well as allowing access to
    the GUI environment.

    ``wants_context`` defaults to ``False`` which corresponds to
    the old protocol without ``ctx``.

So instead of ``activate(self, obj)``, the method should be implemented
as ``activate(self, obj, ctx)``.

The object passed as ``ctx`` has the following interface:

``ctx.register_late_result(result_object)``
    Register the ``result_object`` as a late result. It must be a
    ``Leaf`` or a ``Source``.

``ctx.register_late_error(exc_info=None)``
    Register an asynchronous error. (For synchronous errors, simply raise
    an ``OperationError`` inside ``activate``.)

    For asynchronous errors, call ``register_late_error``. If
    ``exc_info`` is ``None``, the current exception is used.
    If ``exc_info`` is an ``OperationError`` instance, then it is used
    as error. Otherwise, a tuple like ``sys.exc_info()`` can be passed.

``ctx.environment``
    The environment object, which has the following methods:

    ``get_timestamp(self)``
        Return the current event timestamp

    ``get_startup_notification_id(self)``
        Make and return a startup notification id

    ``get_display(self)``
        Return the display name (i.e ``:0.0``)

    ``present_window(self, window)``
        Present ``window`` (a ``Gtk.Window``) on the current
        workspace and monitor using the current event time.


Auxiliary Action Methods
........................

Some auxiliary methods tell Kupfer about how to handle the action:

``is_factory(self)``
    Return ``True`` if the return value of ``activate`` is a source
    that should be displayed immediately.

``has_result(self)``
    Return ``True`` if the action's return value in ``activate`` should
    be selected.

``is_async(self)``
    Return ``True`` if the action returns a ``Task`` object conforming to
    ``kupfer.task.Task`` from ``activate``. The task will be executed
    asynchronously in Kupfer's task queue.

``repr_key(self)``
    Override this to define a unique key for the action,
    if you need to differentiate between different instances of the
    same Action class.

Class Attributes
................

The attribute ``action_accelerator`` is ``None`` by default but
can be a single letter string to suggest a default accelerator for
this action. Actions that act like the default open should use ``"o"``.


Source
::::::

``class Source`` inherits from KupferObject.

A Source understands specific data and delivers Leaves for it.

A Source subclass must at a minimum implement ``__init__``,
``get_items`` and ``provides``.

``Source`` defines, in addition to ``KupferObject``:

``__init__(self, names)``
    You must call this method with a unicode name in the subclass
    ``__init__(self)``.

``get_items(self)``
    Your source should define ``get_items`` to return a sequence
    of leaves which are its items; the return value is cached and used
    until ``mark_for_update`` is called.

    Often, implementing ``get_items`` in the style of a generator (using
    ``yield``) is the most convenient.

    The Leaves shall be returned in natural order (most relevant first),
    or if sorting is required, return in any order and define
    ``should_sort_lexically``.

``get_leaves(self)``
    ``get_leaves`` must not be overridden, define ``get_items``
    instead.

``provides(self)``
    Return a sequence of all precise Leaf types the Source may contain.

    Often, the Source contains Leaves of only one type, in that case
    the implementation is written simply as ``yield ThatLeafType``.

``should_sort_lexically(self)``
    Return ``True`` if the Source's leaves should be sorted
    alphabethically. If not sorted lexically, ``get_items`` should yield
    leaves in order of the most relevant object first (for example the
    most recently used).

``initialize(self)``
    This method is called when the source should be made ready to use.
    This is where it should register for external change callbacks, for
    example.

``finalize(self)``
    This method is called before the Source is disabled (shutdown or
    plugin deactivated).

``get_leaf_repr(self)``
    Return a Leaf that represents the Source, if applicable; for example
    the DirectorySource is represented by a FileLeaf for the directory.

``__hash__`` and ``__eq__``
    Sources are hashable, and equivalents are recognized just like
    Leaves, and the central SourceController manages them so that there
    are no duplicates in the application.

``get_items_forced(self)``
    Like ``get_items``, called when a refresh is forced. By default
    it just calls ``get_items``.

``mark_for_update(self)``
    Should not be overridden. Call ``mark_for_update`` in the source to
    mark it so that it is refreshed by calling ``get_items``.

``repr_key(self)``
    Define to a unique key if you need to differentiate between sources
    of the same class. Normally only used with Sources from factory
    actions or from decorator sources.

``toplevel_source(self)``
    If applicable, the source can return a different source to represent
    it and its objects in the top level of the catalog. The default
    implementation returns ``self`` which is normally what you want.

``is_dynamic(self)``
    Return ``True`` if the Source should not be cached. This is almost
    never used.


Saving Source configuration data
................................

These methods are must be implemented if the Source needs to save
user-produced configuration data.

``config_save_name(self)``
    Return the name key to save the data under. This should almost
    always be literally ``return __name__``

``config_save(self)``
    Implement this to return a datastructure that succintly but
    perfectly represents the configuration data. The returned
    value must be a composition of simple types, that is, nested
    compositions of ``dict``, ``list``, ``str`` etc.

    This is called after ``finalize`` is called on the source.

``config_restore(self, state)``
    The ``state`` parameter is passed in as the saved return value
    of ``config_save``. ``config_restore`` is called before
    ``initialize`` is called on the Source.


Content Decorators
..................

A content-decorating source provides content to a Leaf, where it does
not control the Leaf. An example is the recent documents content
decorator, that provides document collections as content to
applications.

A normal Source listed in ``__kupfer_sources__`` will be eligible for
content decoration as well if it implements the needed methods.
Otherwise content-only sources are listed in ``__kupfer_contents__``.


``@classmethod decorates_type(cls)``
    Return the type of Leaf that can be decorated. You must also
    implement ``decorate_item``.

``@classmethod decorate_item(cls, leaf)``
    Return an instance of a Source (normally of the same type as the
    content decorator itself) that is the content for the object
    ``leaf``.  Return ``None`` if not applicable.

    Sources returned from ``decorate_item`` go into the common Source
    pool. The new source instance will not be used if the returned
    instance is equivalent (as defined by class and ``reepr_key``
    above).
    

Source Attributes
.................

``Source.source_user_reloadable = False``
    Set to ``True`` if the source should have a user-visible
    *Rescan* action. Normally you much prefer to use change
    notifications so that this is not necessary.

``Source.source_prefer_sublevel = False``
    Set to ``True`` to not export its objects to the top level by
    default. Normally you don't wan't to change this

``Source.source_use_cache =  True```
    If ``True``, the source can be pickled to disk to save its
    cached items until the next time the launcher is started.

``Source._version``
    Internal number that is ``1`` by default. Update this number in
    ``__init__`` to invalidate old versions of cache files.


TextSource
::::::::::

TextSource inherits from KupferObject.

A text source returns items for a given text string, it is much like a
simplified version of Source. At a minimum, a TextSource subclass must
implement ``get_text_items`` and ``provides``.

``__init__(self, name)``
    Override as ``__init__(self)`` to provide a unicode name for the
    source.

``get_text_items(self, text)``
    Return a sequence of Leaves for the unicode string ``text``.

``provides(self)``
    Return a sequence of the Leaf types it may contain

``get_rank(self)``
    Return a static rank score for text output of this source.


ActionGenerator
:::::::::::::::

ActionGenerator inherits from object.

ActionGenerator is a helper object that can be declared in
``__kupfer_action_generators__``. It allows generating action objects
dynamically.

``get_actions_for_leaf(self, leaf)``
    Return a sequence of Action objects appropriate for this Leaf

.. note::

    The ``ActionGenerator`` should not perform any expensive
    computation, and not access any slow media (files, network) when
    returning actions.  Such expensive checks must postponed and be
    performed in each Action's ``valid_for_item`` method.


The Plugin Runtime
::::::::::::::::::

.. topic:: How a plugin is activated 

    1. The plugin module is imported into Kupfer.

       If an error occurs, the loading fails and the plugin is disabled.
       If the error raised is an ImportError then Kupfer report it as a
       dependency problem.

    2. Kupfer will initialize a ``kupfer.plugin_support.PluginSettings``
       object if it exists (see next section)

    3. Kupfer will call the module-level function
       ``initialize_plugin(name)`` if it exists.

    4. Kupfer instantiates the declared sources and actions and insert
       sources, actions, content decorators, action generators and text
       sources into the catalog.

.. topic:: When a plugin is deactivated

    When the plugin is disabled, the module-level function
    ``finalize_plugin(name)`` is called if it exists. [It is not yet
    final whether this function is called at shutdown or only when
    hot-unplugging plugins.]

kupfer.plugin_support
:::::::::::::::::::::

This module provides important API for several plugin features.

PluginSettings
..............

To use user-settable configuration parameters, use:

.. code:: python

    __kupfer_settings__ = plugin_support.PluginSettings(
        {
            "key" : "frobbers",
            "label": _("Number of frobbers"),
            "type": int,
            "value": 9,
        },
    )

Where ``PluginSettings`` takes a variable argument list of config
parameter descriptions. The configuration values are accessed with
``__kupfer_settings__[key]`` where ``key`` is from the parameter
description. Notice that ``__kupfer_settings__`` is not updated with
the user values until the plugin is properly initialized.

``PluginSettings`` is read-only but supports the GObject signal
``plugin-setting-changed (key, value)`` when values change.

check_dbus_support and check_keyring_support
............................................

``plugin_support`` provides the convenience functions
``check_dbus_support()`` and ``check_keyring_support()`` that raise the
appropriate error if a dependency is missing.


Alternatives
............

Alternatives are mutually exclusive features where the user must select
which to use. Each category permits one choice.

.. topic:: Categories of Alternatives

    :``terminal``:      the terminal used for running programs that require
                        terminal
    :``icon_renderer``: method used to look up icon names

Each category has a specific format of required data that is defined in
``kupfer/plugin_support.py``. A plugin should use the function
``kupfer.plugin_support.register_alternative(caller, category_key, id_, **kwargs)`` 
to register their implementations of new alternatives. The arguments are:

.. topic:: ``register_alternative(caller, category_key, id_, ** kwargs)``

    :``caller``:       the name of the calling plugin, is always ``__name__``
    :``category_key``: one of the above categories
    :``id_``:          the plugin's identifier for the alternative
    :`kwargs`:         key-value pairs defining the alternative

    ``register_alternative`` is normally called in the plugin's
    ``initialize_plugin(..)`` function.

.. topic:: Fields requried for the category ``terminal``

    :``name``:              unicode visible name
    :``argv``:              argument list: list of byte strings
    :``exearg``:            the execute-flag as a byte string (``""`` when N/A)
    :``desktopid``:         the likely application id as a byte string
    :``startup_notify``:    whether to use startup notification as boolean

.. topic:: Fields required for the category ``icon_renderer``

    :``name``:              unicode visible name
    :``renderer``:          an object with an interface just like
                            ``kupfer.icons.IconRenderer``


Plugin Packages, Resources and Distribution
:::::::::::::::::::::::::::::::::::::::::::

A plugin is a Python module–either a single python file or a folder with
an ``__init__.py`` file (a package module). In the latter case, the
whole of the plugin can be defined inside ``__init__.py``, or it can be
split into several modules. Kupfer will look for all the description
variables (like ``__kupfer_name__``) in ``__init__.py``.

.. topic:: Plugin-installed custom icons

    A package module may include custom icons as .svg files. The icon files
    must be declared in a file inside the python package called
    ``icon-list``. 

    * Each line is a tab-separated field list, with the icon name in
      the first column and the filename (relative to the plugin package)
      in the second column.
    * Lines can be commented with a leading ``#``
    * If a literal ``!override`` appears in the third column, the icon
      is installed even if it overrides the currently used GTK icon
      theme.


Plugins may be installed into any of the ``kupfer/plugins`` data
directories. Package modules can also be installed and used as ``.zip``
files, so they too can be distributed as single files.


Example Plugins
===============

I want to specifically highlight certain files in Kupfer that are good
to read as examples.

+ Custom Leaf and Action: the common case of creating a custom
  ``Leaf`` type and defining its default ``Open`` action, see
  ``kupfer/plugin/notes.py``
+ Content decoration: making content for objects, see
  ``kupfer/plugin/archiveinside.py`` (*Deep Archives* plugin)
+ Asynchronous error reporting: see ``kupfer/plugin/volumes.py``, action
  *Unmount*



Reference to the ``kupfer`` Package
===================================

There are several modules inside the ``kupfer`` package that a plugin
can reuse.

.. topic:: ``kupfer.commandexec``

    ``kupfer.commandexec`` is not used by plugins anymore
    after version v204. See `Auxiliary Method wants_context(self)`_
    above instead.

.. topic:: ``kupfer.config``

    ..

.. topic:: ``kupfer.interface``

    This module does not need to be imported just to implement the
    interface it defines.

    ``TextRepresentation``
        ``get_text_representation``
            If a Leaf has a text representation (used for
            copy-to-clipboard), it should implement this method
            and return a unicode string.

.. topic:: ``kupfer.kupferstring``

    A **byte string** (Python ``str``) is just a stream of data. When
    you handle byte strings that is text, you must convert it to unicode
    as soon as possible. You only know the encoding depending on the
    source of the byte string.

    ``tounicode``
        decode UTF-8 or unicode object into unicode.

    ``tolocale(ustr)``
        coerce unicode ``ustr`` into a locale-encoded bytestring.

    ``fromlocale(lstr)``
        decode locale-encoded bytestring ``lstr`` to a unicode object.


.. topic:: ``kupfer.objects``

    ``kupfer.objects`` includes the basic objects from the package
    ``kupfer.obj``, such as ``Leaf``, ``Action``, ``Source`` etc.

    ``FileLeaf``, ``AppLeaf``, ``TextLeaf`` etc.
        The basic re-usable types live here

    ``OperationError``
        Exception type for user-visible errors in action execution.
        Raise ``OperationError`` with a unicode localized error message
        inside ``Action.activate`` to notify the user of a serious
        error.

        Specialized versions exist: Such as
        ``NotAvailableError(toolname)``,
        ``NoMultiError()``


.. topic:: ``kupfer.pretty``

    ..

.. topic:: ``kupfer.runtimehelper``

    ..

.. topic:: ``kupfer.textutils``

    ..

.. topic:: ``kupfer.uiutils``

    ``show_notification(title, text='', icon_name='', nid=0)``
        Show a notification. If a previous return value is passed as
        ``nid`` , try to replace that previous notification.

        Returns a notification identifier, or None if notifications
        are not supported.

.. topic:: ``kupfer.utils``

    ``spawn_async(argv)``
        Spawn a child process, returning True if successfully started.

    ``spawn_in_terminal(argv)``
        ..

    ``show_path(path)``
        ..

    ``show_url(url)``
        Display with default viewer for ``path`` or ``url``.

    ``get_display_path_for_bytestring(filepath)``
        File paths are bytestrings (and are not text).
        ``get_display_path_for_bytestring`` returns a user-displayable
        text representation as a unicode object.

.. topic:: ``kupfer.task``

    ..

.. topic:: ``kupfer.weaklib``

    ..

.. topic:: ``kupfer.core``

    The module ``kupfer.core`` can not be used by plugins.


.. vim: ft=rst tw=72 et sts=4 sw=4
.. this document best viewed with rst2html
