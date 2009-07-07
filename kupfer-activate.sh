#!/bin/bash

PYTHON="@PYTHON@"
test ${PYTHON:0:1} = "@" && PYTHON=python

# Try to spawn kupfer via dbus, else go to python
# but only if there are no arguments
test -z "$*" && dbus-send --print-reply --dest=se.kaizer.kupfer /interface se.kaizer.kupfer.Listener.ShowHide >/dev/null 2>&1

test $? != 0 && exec ${PYTHON} -m kupfer.__init__ $* || ${PYTHON} -c "import gtk.gdk; gtk.gdk.notify_startup_complete()"
