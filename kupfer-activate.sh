#!/bin/bash

PYTHON="@PYTHON@"
test ${PYTHON:0:1} = "@" && PYTHON=python

# Try to spawn kupfer via dbus, else go to python

# Figure out if there are any options "--help" etc, then launch kupfer
# If there are any non-option arguments, send them to kupfer with PutText
test "x${1:0:2}" = "x--"
KUPFER_HAS_OPTIONS=$?
test -n "$*"
KUPFER_HAS_CLIARGS=$?

test $KUPFER_HAS_OPTIONS != 0 && dbus-send --print-reply --dest=se.kaizer.kupfer /interface se.kaizer.kupfer.Listener.ShowHide >/dev/null 2>&1
KUPFER_RUNNING=$?

test \( $KUPFER_HAS_CLIARGS = 0 -a $KUPFER_HAS_OPTIONS != 0 \) && dbus-send --print-reply --dest=se.kaizer.kupfer /interface se.kaizer.kupfer.Listener.PutText string:"$PWD" string:"$*" >/dev/null 2>&1

test $KUPFER_RUNNING != 0 && exec ${PYTHON} -m kupfer.__init__ $* || ${PYTHON} -c "import gtk.gdk; gtk.gdk.notify_startup_complete()"
