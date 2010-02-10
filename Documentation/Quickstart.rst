======
kupfer
======

-----------------------------------------------------------------
Convenient command and access tool for applications and documents
-----------------------------------------------------------------

:Author: Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
:Date: 17 September 2009
:Manual section: 1

SYNOPSIS
========

| ``kupfer`` [ *OPTIONS* | *QUERY* ]
| ``kupfer-exec`` *FILE* ...

DESCRIPTION
===========

Kupfer is a launcher; you typically use it to summon an application or a
document quickly by typing parts of its name. It can also do more than
getting at something quickly: there are different plugins for accessing
more objects and running custom commands.

Kupfer is written using Python and has a flexible architecture; the
implementation is simple and makes the easy things work first. One goal
is that new plugins can be written quickly without too much programming.

``kupfer-exec`` is a helper script that can execute commands saved to
file, but only by connecting to an already running instace of Kupfer.

SPAWNING
========

Running kupfer on the command line (without options) will try to show
the program it if already running.

If the keybinder module is installed, kupfer will listen to a
keybinding. By default the keybinding is *Ctrl+Space* to show kupfer.

Kupfer can be invoked with a text query, with

        ``kupfer`` *QUERY*

This can be used to select files given as command-line arguments in the
program. Then you can invoke actions even on objects from a shell-based
context.

You may also pipe text to ``kupfer`` to pass it to a currently running
instance of the program.

OPTIONS
=======

--no-splash     Launch without presenting main interface

--list-plugins  Display a list of all installed plugins

--debug         Enable more verbose output that can help understanding
                the program's operation.

The following are generic options

--help          Display usage information

--version       Display version information

CONFIGURATION
=============

Custom plugins are added to kupfer by installing them to the directory
*~/.local/share/kupfer/plugins*, or any kupfer/plugins directory in any
of ``$XDG_DATA_DIRS``.

.. vim: ft=rst tw=72
.. this document best viewed with::
        rst2pdf Quickstart.rst && xdg-open Quickstart.pdf
