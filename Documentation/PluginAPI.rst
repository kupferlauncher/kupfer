=================
Kupfer Plugin API
=================

:Author: Ulrik Sverdrup
:Date: Sunday, 20 March 2011
:Homepage: http://kaizer.se/wiki/kupfer

.. contents::


Introduction
============

Kupfer is a Python program that allows loading extension modules
at runtime. One plugin is equivalent to one Python module implemented
as one .py file or a Python package.

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

Plug-ins live in the package ``kupfer.plugin``. Kupfer also includes
directories called ``kupfer/plugins`` from XDG_DATA_DIRS which typically
means ``/usr/share/kupfer/plugins`` and
``$HOME/.local/share/kupfer/plugins``. These directories are
transparently included into the kupfer package, so the user has multiple
choices of where to install plugins.

The Plugin File
---------------

A kupfer plugin is a ``.py`` file with some special attributes.

It starts like this (an imagined example)::

    __kupfer_name__ = _("Cool X-Documents")
    __kupfer_sources__ = ("DocumentSource", )
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ("Open", )
    __description__ = _("Documents from the X program")
    __version__ = "1"
    __author__ = "Tom Author"

For a plugin, the following attributes are required::

    __kupfer_name__ (Localized name of plugin)
    __description__ (Localized description of plugin)
    __version__
    __author__

For the plugin to do anything, the following attributes may be defined::

    __kupfer_sources__ = ()
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ()
    __kupfer_action_generators__ = ()

They should be tuples of *names* of classes in the module:

* all sources have to be subclasses of ``kupfer.objects.Source``
* all text sources have to be subclasses of ``kupfer.objects.TextSource``
* all actions have to be subclasses of ``kupfer.objects.Action``

So your example plugin declaring::

    __kupfer_sources__ = ("DocumentSource", )

will later in the file define this class::

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
action that works with all FileLeaf.


A Short Working Example
-----------------------

The very simplest thing we can do is to provide an action on
objects that already exist in Kupfer. These actions appear in the right
hand actions pane in kupfer, when an object of the right type is
selected.

The complete plugin python code::

    __kupfer_name__ = _("Image Viewer")
    __kupfer_actions__ = ("View", )
    __description__ = _("View images quickly")
    __version__ = ""
    __author__ = "Tom Author"

    import gtk

    from kupfer.objects import Action, FileLeaf

    class View (Action):
        def __init__(self):
            Action.__init__(self, _("View"))

        def item_types(self):
            yield FileLeaf

        def valid_for_item(self, fileobj):
            return fileobj.object.endswith(".jpg")

        def activate(self, fileobj):
            image_widget = gtk.Image()
            image_widget.set_from_file(fileobj.object)
            image_widget.show()
            window = gtk.Window()
            window.add(image_widget)
            window.present()

That is all. We do the following:

* Declare a plugin called "Image Viewer" with an action class ``View``.
* ``View`` declares that it works with ``FileLeaf``
* ``View`` only accepts ``FileLeaf`` that end with '.jpg'
* ``View`` defines a method ``activate`` that when called, will use gtk
  to show the file in a window

.. note::

    Kupfer uses a very simplified programming style of composition and
    cooperative superclasses.

    You normally never call a superclass implementation inside a method
    that you define, with the exception of ``__init__``.

    On the other hand, there are superclass methods that should not be
    overridden. For example, ``KupferObject.get_pixbuf`` is never
    overridden, instead you implement ``KupferObject.get_icon_name``.


Reference
=========

Kupfer's architecture is built around objects that can be acted on by
actions. Kupfer's basic concept for understanding objects is in
``kupfer/obj/base.py``. The basic building block is ``KupferObject``.

KupferObject
------------

base class for basic user-visible constructs, this defines:

* A way to get the object's name
* A way to get the object's description
* A way to get the object's icon

This is the base object for the following four very important base
classes:

* Leaf
* Action
* Source
* TextSource
* ActionGenerator

Below follows a summary. For complete information, you should read
kupfer's python interface documentation: go to the directory containing
the kupfer module and do::

    $ pydoc kupfer.obj.base

or equivalently::

    $ python
    >>> import kupfer.obj.base
    >>> help(kupfer.obj.base)

Leaf
----

A Leaf represents an object that the user will want to summon and
act on. An example is a file, an application, a window or a Free-text
query (TextLeaf).

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
    Returns the *builtin* Actions for a Leaf; builtin Actions are such
    that do not apply generally, but only to Leaves defined in a
    particular module or Plugin.

``__hash__`` and ``__eq__``
    Leaves are hashable, can be members in a set, and duplicates are
    recognized (and removed); this is essensial so that equivalent
    Leaves from different sources are recognized. By default duplicates
    are recognized if both the name and the ``Leaf.object`` property are
    the same.

``has_content()`` and ``content_source()``
    These methods are used to find out if the object contain anything,
    like a folder contains files or a music album songs.
    If the Leaf should have content, it should override ``has_content``
    to return ``True`` and define ``content_source()`` to return
    an instance of a Source.
    A Leaf may decide dynamically if it has content or not.

Action
------

An Action represents a command using a direct object and an optional
indirect object. One example is ``kupfer.obj.fileactions.Open`` that
will open its direct object (which must be a file), with its default
viewer.

Actions are the most versatile parts of Kupfer, since they can define
ways to use objects together. They also have to decide, which types of
Leaves they apply to, and if they apply to a given Leaf.

Action defines, in addition to KupferObject:

``activate(leaf, obj)``
    Called to perform its effect on a Leaf, where ``obj`` is the
    (optional) indirect object.

``item_types()``
    This method returns all the types of Leaves that the action
    applies to (direct object).
``valid_for_item(item)``
    Return whether action applies to ``item`` or not, which is of
    one of the types returned by ``item_type.``

``requires_object()``
    Whether this action uses an indirect object or not. If the Action
    requires an indirect object, it must also define (at least)
    ``object_types``.
``object_types()``
    Return all the types of Leaves that are valid for the action's
    indirect object.
``object_source(for_item)``
    If the action's indirect objects should not be picked from the full
    catalog, but from a defined source, return an instance of the Source
    here, else return None.
``valid_object(obj, for_item)``
    This method, if defined,  will be called for each indirect object
    (with the direct object as ``for_item``), to decide if it can be
    used.

Some auxiliary methods tell Kupfer about how to handle the action:

``is_factory()``
    If the action returns content, return a collection of new items.
``has_result()``
    If the action's return value in activate should treated as the new
    selection.
``is_async()``
    If the action returns a ``Task`` object conforming to
    ``kupfer.task.Task``. The task will be executed asynchronously in
    Kupfer's task queue.

Source
------

A Source understands specific data and delivers Leaves for it. For
example DirectorySource, that will give FileLeaves for contents of a
directory.

This defines, in addition to KupferObject:

``get_items()``
    Source subclasses should define ``get_items`` to return its items;
    the items are cached automatically until ``mark_for_update`` is
    called.
``is_dynamic()``
    Return ``True`` if the Source should not be cached. A source should
    almost never be dynamic.
``should_sort_lexically()``
    Return ``True`` if the Source's leaves should be sorted
    alphabethically. If not sorted lexically, ``get_items`` should yield
    leaves in order of the most relevant object first (for example the
    most recently used).
``provides()``
    Return a sequence of all precise Leaf types the Source may contain

``initialize()``
    Called when the source should be made ready to use. This is where it
    should register for external change callbacks, for example.

``get_leaf_repr()``
    Return a Leaf that represents the Source, if applicable; for example
    the DirectorySource is represented by a FileLeaf for the directory.
``__hash__`` and ``__eq__``
    Sources are hashable, and equivalents are recognized just like
    Leaves, and the central SourceController manages them so that there
    are no duplicates in the application.

TextSource
----------

A text source returns items for a given text string, it is much like a
simplified version of Source.

``get_text_items(text)``
    Return items for the given query.
``provides()``
    Return a sequence of the Leaf types it may contain

.. vim: ft=rst tw=72 et sts=4
.. this document best viewed with rst2html
