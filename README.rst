kupfer is a simple, flexible launcher for GNOME
++++++++++++++++++++++++++++++++++++++++++++++++

:Homepage:  https://wiki.gnome.org/Apps/Kupfer
:Credits:   Copyright 2007–2011 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
:Licence:   GNU General Public License v3 (or any later version)

Kupfer is an interface for quick and convenient access to applications
and their documents.

The most typical use is to find a specific application and launch it. We
have tried to make Kupfer easy to extend with plugins so that this
quick-access paradigm can be extended to many more objects than just
applications.

Installing
==========

This project is configured for the Waf build system;
Installation follows the steps::

    ./waf configure
    ./waf

then::

    ./waf install

or ::

    sudo ./waf install

You can use ``--prefix=$PREFIX`` when configuring to assign an
installation spot. By default, Kupfer is installed for all users.
Installing only for your user, the prefix ``~/.local`` is often used;
you just have to make sure that ``~/.local/bin`` is in your ``$PATH``.


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

    No file contents touched.

Build Requirements
------------------

* Python 2.6 or Python 3
* intltool
* optionally: rst2man (python-docutils)  to install the manpage
* optionally: xml2po (gnome-doc-utils)  to install mallard help pages

Runtime Requirements
--------------------

Kupfer requires Python 2.6 or later, and the following important libraries:

* gtk python bindings, GTK+ version 2.20 [#]_
* glib python bindings (pygobject) 2.18
* dbus python bindings
* python-xdg

.. [#] GTK+ 2.20 required for using full support. Kupfer is known to run with
       version 2.18 as well.

Optional, but very recommended runtime dependencies:

* python-keybinder (see below)
* wnck python bindings
* gvfs
* `keyring` python module

Opportunistic dependencies

* The deprecated 'gnome' module is used for session connection as
  fallback
* If available, 'setproctitle' is used to set the process name
* python-appindicator for ubuntu-style notification icon

* nautilus-python for nautilus selected file
* python-gdata for Google plugins

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

.. _`Keybinder`: http://kaizer.se/wiki/keybinder

You can use kupfer without the keybinder module, for example by
assigning a global keybinding to the ``kupfer`` binary, but it not the
recommended way.

Documentation
=============

Please read ``Documentation/`` and ``Documentation/Manpage.rst`` for
technical documentation. User documentation is installed as GNOME
(Mallard) help pages, available under the "Kupfer Help" object in the
program itself.

.. vim: ft=rst tw=72
