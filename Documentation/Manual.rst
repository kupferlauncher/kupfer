======
kupfer
======

:Author: Ulrik Sverdrup
:Date: Friday, 18 September 2009
:License: GNU General Public License, version 3
:Homepage: http://kaizer.se/wiki/kupfer

.. contents::

Kupfer internals
================

Kupfer's architecture is built around objects that can be acted on by
actions. Kupfer's basic concept for understanding objects is in
``kupfer/objects.py``. The basic building block is ``KupferObject``.

.. note::

    This document is a Work in progress.

    If you have questions, just fire them away directly to me,
    using the address <ulrik.sverdrup@gmail.com>


KupferObject
------------

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
    >>> import kupfer.main
    >>> import kupfer.objects
    >>> help(kupfer.objects.KupferObject)
    >>> help(kupfer.objects.Leaf)
    >>> help(kupfer.objects.Action)
    >>> help(kupfer.objects.Source)


Leaf
----

this represents an object that the user will want to summon and
act on. An example is a file, an application, a window or a Free-text
query (TextLeaf).

This defines, in addition to KupferObject:

* ``Leaf.object`` is the represented object, is implementation-specific
* A way to get the default actions for this type
* ``__hash__`` and ``__eq__`` so that equivalents are recognized
* ``has_content()`` and ``content_source()`` to find out if objects
  contain anything, like for example folders do

Action
------

represents and action on a Leaf, for example Show() that will open with
default viewer.

This defines, in addition to KupferObject:

* ``activate(leaf, obj)`` to act on a leaf, with optional indirect object
* ``is_factory`` if the action returns content, returns a collection of
  new items.
* ``item_type``: which items action applies to (in plugins)
* ``require_object``: Wheter this action uses an indirect object; if it
  does, some more methods have to define which items

Source
------

The Source understands specific data and delivers Leaves for it. For
example DirectorySource, that will give FileLeaves for contents of a
directory.

This defines, in addition to KupferObject:

* ``__hash__`` and ``__eq__`` so that equivalents are recognized
* ``get_items`` That subclasses should define to return its items
* ``is_dynamic`` If there should be no caching (usually there should be)
* ``get_leaf_repr`` How to represent the source in a list, For example
  the DirectorySource is represented by a FileLeaf for the directory
* ``provides`` To define which Leaf types it may contain

TextSource
----------

A text source returns items for a given text string

* ``get_item`` produce items for given string
* ``provides`` To define which Leaf types it may provide

Strings
-------

Kupfer deals with PyGTK a lot, which always returns UTF-8-encoded
strings (almost always). However Kupfer works internally with unicode
strings; only then does slicing, lowercasing etc work across other than
ascii charsets.
Kupfer accepts UTF-8-encoded strings as well as unicode objects for the
most parts, but all internals should be unicode. Note that the gettext
``_()`` will return a unicode string.

Plugins
=======

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
============

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
-------------------

Most of kupfer plugin code uses super statements such as::

	super(RecentsSource, self).__init__(_("Recent items"))

when writing new code, you should however use the following style::

	Source.__init__(self, _("Recent items"))

Why? Because the second version is easier to copy! If you copy the whole
class and rename it, which you often do to create new plugins, you have
don't have to-- you are probably using the same superclass.

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

Add the language to po/LINGUAS with it's (commonly) two-letter code.
Run ./waf intlupdate and then edit the header in the po/lang.po file,
filling in your name and other slots, and importantly the CHARSET. You
probably want to use UTF-8.

When the header is filled-in, run ./waf intlupdate to see that it runs
without errors, and you should have a po/lang.po file ready for
translating.

To try the new translation
--------------------------

Make sure the translation is listed in po/LINGUAS.

To try it, you have to install kupfer with ``./waf install``

If you run ./kupfer-activate.sh from the working directory it won't find
the installed translations unless you make a symlink called ``locale`` to
the installed location (for example ``~/.local/share/locale`` if install
prefix was ``~/.local``).

.. vim: ft=rst tw=72
.. this document best viewed with::
        TMP=$(tempfile); rst2html Manual.rst > $TMP; xdg-open $TMP
