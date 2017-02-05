====================
GTK+ Theming Support
====================

----------------------------
Changing Kupfer's Appearance
----------------------------

.. contents::


Introduction
============

In Kupfer's the interface elements are marked-up with names and classes
so that Gtk 3's css mechanism can style them.

The work is not yet complete.

Existing widget names:

#kupfer 
    main window

#kupfer-object-pane, #kupfer-action-pane, #kupfer-indirect-object-pane
    the three panes

.matchview
    a pane's view

#kupfer-list
    result list window

#kupfer-list-view
    result list tree view


Icons
=====

The kupfer-specific icon names we use are:

+ ``kupfer``  (application)
+ ``kupfer-catalog``  (root catalog)
+ ``kupfer-execute`` (default action icon)
+ ``kupfer-launch``  (default launch icon)
+ ``kupfer-object``  (blue box generic object icon)
+ ``kupfer-object-multiple`` (multiple generic objects)

.. vim: ft=rst tw=72 et sts=4 sw=4
.. this document best viewed with rst2html
