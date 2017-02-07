kupfer is a simple, flexible launcher
+++++++++++++++++++++++++++++++++++++

:Homepage:  https://kupferlauncher.github.io/
:Credits:   Copyright 2007–2017 Ulrik Sverdrup and other Kupfer authors
:Licence:   GNU General Public License v3 (or any later version)

Kupfer is an interface for quick and convenient access to applications
and their documents.

The most typical use is to find a specific application and launch it. We
have tried to make Kupfer easy to extend with plugins so that this
quick-access paradigm can be extended to many more objects than just
applications.

Installing
==========

This project is configured for the Waf build system, which is included.
Run it using either ``./waf`` or ``python3 waf`` (using your python.)

Installation follows the steps::

    ./waf configure
    ./waf

If configure does not find the right Python 3 executable, set ``PYTHON``
explicitly first.

then::

    ./waf install

or ::

    sudo ./waf install

You can use ``--prefix=$PREFIX`` when configuring to assign an
installation spot. By default, Kupfer is installed for all users.
Installing only for your user is possible, but the binary directory must
be in your ``$PATH``.

About Waf
---------

Waf is included in both the distributable tarball and the repository (so
that full source code is incuded. See the file `waf` for author and
licensing information).

Waf was acquired through http://waf.googlecode.com/files/waf-1.6.11.tar.bz2
on Saturday, 25 February 2012. The following files extracted::

    ./waf-light -> ./waf
    ./waflib    -> ./waflib
    ./ChangeLog -> ./Waf.ChangeLog

    ./waflib/Tools/*  some files excluded
    ./waflib/extras/* some files excluded

1 patch as been applied to waf.

Build Requirements
------------------

* Python 3
* intltool
* optionally: rst2man (python-docutils)  to install the manpage
* optionally: xml2po (gnome-doc-utils)  to install mallard help pages

Runtime Requirements
--------------------

Kupfer requires Python 3 or later, and the following important libraries:

Because the port to Python 3 and Gtk 3 is new, I don't know what the lower
boundaries of dependencies are. I've given the versions where it is
known to work.

* Gtk-3.0 version 3.22
* Wnck-3.0 version 3.20
* libkeybinder-3.0 version 0.3.1
* python gir1.2
* dbus python bindings
* python-xdg

Opportunistic dependencies

* If available, 'setproctitle' is used to set the process name

Recommended dependencies

* Yelp, the help browser

Some plugins will require additional python modules!

Spawning
========

The program is installed as ``kupfer`` into ``$PREFIX/bin``. Only one
instance can be active for one user at a given time. Normal use of
kupfer requires an active dbus session bus.

Keybinder Module
----------------

Keybinder_ is a module for global keyboard shortcuts that originates
from tomboy.

.. _`Keybinder`: https://github.com/engla/keybinder

(Temporarily: Keybinder is required. We want to fix that).
You can use kupfer without the keybinder module, for example by
assigning a global keybinding to the ``kupfer`` binary, but it not the
recommended way.

Documentation
=============

The user’s guide is installed as Mallard help pages, available under the
“Kupfer Help” object in the program itself; it is also on the web page.
Kupfer will use the help browser if there is a handler for the ``help:`` URI
scheme. The user’s guide’s source is under ``help/``, and it is translatable.

Please read ``Documentation/`` and ``Documentation/Manpage.rst`` for
technical and contributor documentation.

.. vim: ft=rst tw=78
