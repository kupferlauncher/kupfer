======
kupfer
======

:Author: Ulrik Sverdrup
:Date: Wednesday, 23 September 2009
:Revision: $Id$
:Homepage: http://kaizer.se/wiki/kupfer

.. contents::

Kupfer internals
================

Building blocks
---------------

Kupfer's architecture is built around objects that can be acted on by
actions. Kupfer's basic concept for understanding objects is in
``kupfer/objects.py``. The basic building block is ``KupferObject``.

.. note::

    This document is a Work in progress.

    If you have questions, just fire them away directly to me,
    using the address <ulrik.sverdrup@gmail.com>


KupferObject
............

base class for basic user-visible constructs, this defines:

* A way to get the object's name
* A way to get the object's icon

This is the base object for the following four very important base
classes:

* Leaf
* Action
* Source
* TextSource

Below follows a summary. For complete information, you should read
kupfer's python interface documentation: go to the directory containing
the kupfer module and do::

    $ python
    >>> from kupfer import main, objects
    >>> help(objects.KupferObject)
    >>> help(objects.Leaf)
    >>> help(objects.Action)
    >>> help(objects.Source)

Leaf
....

A Leaf represents an object that the user will want to summon and
act on. An example is a file, an application, a window or a Free-text
query (TextLeaf).

This defines, in addition to KupferObject:

``Leaf.object``
    ``Leaf.object`` is the represented object, which is the
    implementation-specific internal data.

``get_actions``
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

Action
......

An Action represents a command using a direct object and an optional
indirect object. One example is ``objects.Show`` that will open its
direct object (which must be a file), with its default viewer.

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
......

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

``get_leaf_repr()``
    Return a Leaf that represents the Source, if applicable; for example
    the DirectorySource is represented by a FileLeaf for the directory.
``__hash__`` and ``__eq__``
    Sources are hashable, and equivalents are recognized just like
    Leaves, and the central SourceController manages them so that there
    are no duplicates in the application.

TextSource
..........

A text source returns items for a given text string, it is much like a
simplified version of Source.

``get_item(text)``
    Return items for the given query.
``provides()``
    Return a sequence of the Leaf types it may contain

Strings
-------

Kupfer deals with PyGTK a lot, which always returns UTF-8-encoded
strings (almost always). However Kupfer works internally with unicode
strings; only then does slicing, lowercasing etc work across other than
ascii charsets.
Kupfer accepts UTF-8-encoded strings as well as unicode objects for the
most parts, but all internals should be unicode. Note that the gettext
function ``_()`` will return a unicode string.

Plugins
-------

A kupfer plugin is a python module with special module attributes

Here is an example from ``kupfer.plugin.applications``::

    __kupfer_name__ = _("Applications")
    __kupfer_sources__ = ("AppSource", )
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ("OpenWith", )
    __description__ = _("All applications and preferences")
    __version__ = ""
    __author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

For a plugin, the following attributes are required::

    __kupfer_name__ (Localized name of plugin)
    __description__ (Localized description of plugin)
    __version__
    __author__

For the plugin to do anything, the following attributes may be defined::

    __kupfer_sources__ = ()
    __kupfer_text_sources__ = ()
    __kupfer_actions__ = ()

They should be tuples of *names* of classes in the module:

* all sources have to be subclasses of ``kupfer.objects.Source``
* all text sources have to be subclasses of ``kupfer.objects.TextSource``
* all actions have to be subclasses of ``kupfer.objects.Action``

The plugin should not do **anything at all** upon module load, except
loading its required modules. Load modules without try/except;
ImportErrors will be caught by the plugin loader and the plugin disabled

Look in ``contrib/`` and in ``kupfer/plugin/`` for using the existing
plugins as example

Coding style
------------

Kupfer python code is indented with tabs, which is a bit uncommon. (My
editor is set to tabs of size four.) Otherwise, if you want to
contribute to kupfer keep in mind that

* Python code should be clear
* Kupfer is a simple project. Do simple first.

Sometimes comments are needed to explain the code. How many know the
``for..else`` construction? Hint: find out what it does in the
``kupfer.icons`` module::

    for item in sequence:
        ...
    else:
        ...

Living and learning
...................

Most of kupfer plugin code uses super statements such as::

    super(RecentsSource, self).__init__(_("Recent items"))

when writing new code, you should however use the following style::

    Source.__init__(self, _("Recent items"))

Why? Because the second version is easier to copy! If you copy the whole
class and rename it, which you often do to create new plugins, the
second version does not need to be updated -- you are probably using the
same superclass.

Localization
============

kupfer is translated using gettext and it is managed in the build system
using intltool. Translation messages are located in the po/ directory.

To update or check an existing translation
------------------------------------------

To update with new strings, run::

    ./waf intlupdate

Then check all fuzzy messages, translate all untranslated messages.
Continue running ``./waf intlupdate`` to check that you have 0 fuzzy and
0 untranslated, then you're finished. ``./waf intlupdate`` will also run
a check of the consistency of the file, so that you know that all syntax
is correct.

If you want to send in the translation to a repository, or as a patch,
you can use git if you have a checked-out copy of kupfer::

    git add po/lang.po
    git commit -m "lang: Updated translation"

    # now we create a patch out of the latest change
    git format-patch HEAD^

where ``lang`` is the two-letter abbreviation. You can send the patch to
the mailing list kupfer-list@gnome.org.


To create a new translation
---------------------------

Add the language to ``po/LINGUAS`` with its (commonly) two-letter code.
Run ``./waf intlupdate`` and then edit the header in the ``po/lang.po``
file, filling in your name and other slots, and importantly the CHARSET.
Kupfer translations *must* use the UTF-8 encoding.

When the header is filled-in, run ``./waf intlupdate`` to see that it
runs without errors, and you should have a ``po/lang.po`` file ready for
translating.

To try the new translation
--------------------------

Make sure the translation is listed in ``po/LINGUAS``.

To try it, you have to install kupfer with ``./waf install``

If you run ``./kupfer-activate.sh`` from the working directory it won't
find the installed translations unless you make a symlink called
``locale`` to the installed location (for example
``~/.local/share/locale`` if install prefix was ``~/.local``).


Copyright
=========

The program Kupfer is released under the
`GNU General Public Licence v3`:t: (or at your option, any later
version). Please see the main program file for more information.

This documentation is released under the same terms as the main
program. The documentation sources are available inside the Kupfer
source distribution.

Copyright 2009, Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

.. vim: ft=rst tw=72
.. this document best viewed with::
        rst2pdf Manual.rst && xdg-open Manual.pdf
