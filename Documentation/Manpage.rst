======
kupfer
======

-----------------------------------------------------------------
Convenient command and access tool for applications and documents
-----------------------------------------------------------------

:Author: Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
:Date: 2011
:Manual section: 1

SYNOPSIS
========

| ``kupfer`` [ *OPTIONS* | *FILE* ... ]
| ``kupfer-exec`` *FILE* ...

DESCRIPTION
===========

Kupfer is an interface for quick and convenient access to applications
and their documents.

The most typical use is to find a specific application and launch it. We
have tried to make Kupfer easy to extend with plugins so that this
quick-access paradigm can be extended to many more objects than just
applications.

``kupfer-exec`` is a helper script that can execute commands saved to
file, but only by connecting to an already running instance of Kupfer.

SPAWNING
========

Running kupfer on the command line (without options) will try to show
the program it if already running.

Kupfer can be invoked with a list of files

        ``kupfer`` *FILE* ...

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

--relay         Run libkeybinder relay service on the current
                ``$DISPLAY``. kupfer is supported in a multihead
                configuration with multiple X screens, if it all exists
                inside one single desktop (and D-Bus) session.

                On the first X screen, kupfer should be started
                normally. For each additional screen with unique
                ``$DISPLAY`` name, the relay service must be started. It
                will pass on the summoning and trigger global keyboard
                shortcuts.

                ``kupfer --relay`` will wait if no running kupfer can be
                contacted. It never exits until interrupted.

The following are generic options

--help          Display usage information

--version       Display version information

CONFIGURATION
=============

Custom plugins are added to kupfer by installing them to the directory
*~/.local/share/kupfer/plugins*, or any kupfer/plugins directory in any
of ``$XDG_DATA_DIRS``.

ENVIRONMENT VARIABLES
=====================

If *KUPFER_NO_CUSTOM_PLUGINS* is set, only allow loading built-in
plugins (installed in the program's python package).

If *KUPFER_NO_CACHE* is set, do not load from or write to any source
cache files.


.. vim: ft=rst tw=72
.. this document best viewed with::
        rst2pdf Quickstart.rst && xdg-open Quickstart.pdf
