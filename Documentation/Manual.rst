======
kupfer
======

:Author: Ulrik Sverdrup
:Date: Sunday,  1 November 2009
:Revision: $Id$
:Homepage: http://kaizer.se/wiki/kupfer

.. contents::

Kupfer internals
================

Building blocks
---------------

Kupfer's architecture is built around objects that can be acted on by
actions. Kupfer's basic concept for understanding objects is in
``kupfer/obj/base.py``. The basic building block is ``KupferObject``.

Further built-in objects are defined in all of the ``kupfer/obj``
package, most importantly in ``kupfer/obj/objects.py``.

.. note::

    This document is a Work in progress.

    If you have questions, just email them away directly to me.


KupferObject
............

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

Below follows a summary. For complete information, you should read
kupfer's python interface documentation: go to the directory containing
the kupfer module and do::

    $ pydoc2.6 kupfer.obj.base

or equivalently::

    >>> import kupfer.obj.base
    >>> help(kupfer.obj.base.KupferObject)
    >>> help(kupfer.obj.base)

Leaf
....

A Leaf represents an object that the user will want to summon and
act on. An example is a file, an application, a window or a Free-text
query (TextLeaf).

This defines, in addition to KupferObject:

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

Action
......

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
..........

A text source returns items for a given text string, it is much like a
simplified version of Source.

``get_text_items(text)``
    Return items for the given query.
``provides()``
    Return a sequence of the Leaf types it may contain

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

Guidelines and Policy
=====================

Contributing
------------

You can clone git from its official repository at git.gnome.org, see:

    http://git.gnome.org/browse/kupfer/

You can structure your changes into a series of commits in git. A series
of well disposed changes is easy to review. Write a sufficient commit
log message for each change. Do not fear writing down details about
why the change is implemented as it is, if there are multiple
alternatives. Also, if you forsee any future possibilites or problems,
please describe them in the commit log.

It is not easy to write good commit messgages, because writing is an
art. It is however essensial, and only by trying it, can you improve.

You may publish your changes by sending an email to the mailing list,
<kupfer-list@gnome.org>. You can attach your changes as patches, or you
may also just attach a link to your published git repository.

You can find kupfer's `git repository at github`__ and fork it there,
for easy publication of your changes.

If you suggest your changes for inclusion into Kupfer, make sure you
have read the whole *Guidelines and Policy* chapter of this manual. And
take care to structure your changes, do not fear asking for advice. Good
Luck!

__ http://github.com/engla/kupfer


Icon Guidelines
---------------

Consider the following:

* A Leaf is an object, a metaphor for a physical thing. It can have as
  detailed icon as is possible.

* An Action is a verb, a command that can be carried out. Choose its
  name with care. The icon should be simple, maybe assign the action
  to a category, rather than trying to illustrate the action itself.
  For example, all text display actions use the "bold style" icon, in
  some icon themes simply a bold "A".

.. important::

    Actions should have stylized, simple icons. Leaves and Sources
    should have detailed, specific icons.


Coding style
------------

Kupfer python code is indented with tabs, which is a bit uncommon. (My
editor is set to tabs of size four.) Otherwise, if you want to
contribute to kupfer keep in mind that

* Python code should be clear
* Kupfer is a simple project. Do simple first. [#simple]_

Python's general style guideline is called `PEP 8`_, and you should
programmers should read it. The advice given there is very useful when
coding for Kupfer.

.. _`PEP 8`: http://www.python.org/dev/peps/pep-0008/

.. [#simple] Writing simple code is more important than you think.
             Read your diff (changes) when you are finished writing a
             feature. Can you make it more simple to read? If you can
             make it simpler, often a more effective algorithm comes out
             of it at the same time. All optimizations have a price,
             and unless you measure the difference, abstain from
             optimizations.


Specific Points
---------------

Using ``rank_adjust``
.....................

A declaration like this can modify the ranking of an object::

    class MyAction (Action):
        rank_adjust = -5
        ...

1. Often, this is useless. Don't use it, let Kupfer learn which actions
   are important.

2. If the action is destructive, the adjust should be negative. Never
   positive. For example *Move to Trash* has a negative 10
   ``rank_adjust``.

3. If the action is very general, and applies to almost everything but
   still should never be the default for anything, the adjust should be
   negative.


Using ``super(..)``
...................

Many of kupfer plugin code uses super statements such as::

    super(RecentsSource, self).__init__(_("Recent items"))

We have learnt that it is not so practical. Therefore, when writing new
code, you should however use the following style::

    Source.__init__(self, _("Recent items"))

Why? Because the second version is easier to copy! If you copy the whole
class and rename it, which you often do to create new plugins, the
second version does not need to be updated -- you are probably using the
same superclass.

Text and Encodings
..................

Care must be taken with all input and output text and its encoding!
Internally, kupfer must use ``unicode`` for all internal text.
The module ``kupfer.kupferstring`` has functions for the most important
text conversions.

Two good resources for unicode in Python are to be found here:

| http://farmdev.com/talks/unicode/
| http://www.amk.ca/python/howto/unicode

**Always** find out what encoding you must expect for externally read
text (from files or command output). If you must guess, use the locale
encoding.
Text received from PyGTK is either already unicode or in the UTF-8
encoding, so this text can be passed to ``kupferstring.tounicode``.

Note that the gettext function ``_()`` always returns a unicode string.


Localization
============

kupfer is translated using gettext and it is managed in the build system
using ``intltool``. Translation messages are located in the ``po/``
directory.

Kupfer's localizations are listed among GNOME's modules. Its homepage
is:

    http://l10n.gnome.org/module/kupfer/

You can download the latest version of your language's translation file
there, if Kupfer is already translated to your language.


To create a new translation
---------------------------

Go into the directory ``po``

1. Add the language code ``$LANG`` to the file ``LINGUAS``
2. Run ``intltool-update --pot``, and copy ``untitled.pot`` to ``$LANG.po``
3. Edit and check the whole file header: 

   + Write in yourself as author
   + Check ``plurals`` (copy from a language that you know uses the same
     number of plural forms, or look up in GNOME's translation pages.)
   + Replace everything written in CAPS

Fill in the charset used; Kupfer translations *must* use the UTF-8 encoding.

When the header is filled-in, go to `To update or check an existing
translation`_


To update or check an existing translation
------------------------------------------

Go to your Kupfer source directory.

Here we will call your language ``$LANG``. You should use a two or
four-letter code for your language instead of ``$LANG``, for example
"de" for German or "pt_BR" for Brazilian Portuguese.

Go to the translation directory ``po``::

    cd po/

To update and check the translation file, run::

    intltool-update $LANG

Now check and edit ``$LANG.po``. Search for all messages marked "fuzzy",
and remove the word "fuzzy" from them when they are done.

Continue running ``intltool-update $LANG`` and check that you have 0
fuzzy and 0 untranslated, then you're finished.

This will also check consistency of the file, so that you know that all
your syntax is correct.

If you want to send in the translation to a repository, or as a patch,
you can use git if you have a checked-out copy of kupfer::

    git add po/$LANG.po
    git commit -m "$LANG: Updated translation"

    # now we create a patch out of the latest change
    git format-patch HEAD^

You can send the patch, or the whole file, to the mailing list
kupfer-list@gnome.org.

To try the new translation
--------------------------

Make sure the translation is listed in ``po/LINGUAS``.

To try it, you have to install kupfer with ``./waf install``, then you
can run kupfer as normal.

.. note::

    If you run ``./kupfer-run`` from the source directory it won't
    find the installed translations unless you make a symlink called
    ``locale`` to the installed location (for example
    ``~/.local/share/locale`` if install prefix was ``~/.local``)::

        $ ln -s ~/.local/share/locale


Copyright
=========

The program Kupfer is released under the
`GNU General Public Licence v3`:t: (or at your option, any later
version). Please see the main program file for more information.

This documentation is released under the same terms as the main
program. The documentation sources are available inside the Kupfer
source distribution.

Copyright 2009, Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

.. vim: ft=rst tw=72 et sts=4
.. this document best viewed with::
        rst2pdf Manual.rst && xdg-open Manual.pdf
