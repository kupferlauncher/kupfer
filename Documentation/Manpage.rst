======
kupfer
======

-----------------------------------------------------------------
Convenient command and access tool for applications and documents
-----------------------------------------------------------------

:Author: Ulrik Sverdrup
:Date: 2017
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

The file paths will be sent to and selected in an already running
instance of the program.

You may also pipe text to ``kupfer`` to pass it to a currently running
instance.

OPTIONS
=======

--no-splash     Launch without presenting main interface

--debug         Enable more verbose output that can help understanding
                the program's operation.

--list-plugins  List all installed plugins by their identifier, version
                and description.

The following are options for internal use

--exec-helper=HELPER    Run plugin helper program, which should be the
                        name of a module inside kupfer.

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

If *KUPFER_NO_KEYBINDER* is set do not use ``Keybinder`` even if it is
installed.


.. vim: ft=rst tw=72
.. this document best viewed with::
        rst2pdf Quickstart.rst && xdg-open Quickstart.pdf
