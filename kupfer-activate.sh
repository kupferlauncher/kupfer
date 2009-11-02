#!/bin/bash

PYTHON="@PYTHON@"
test ${PYTHON:0:1} = "@" && PYTHON=python

# Try to spawn kupfer via dbus, else go to python

# Figure out if there are any options "--help" etc, then launch kupfer
test "x${1:0:2}" = "x--"
KUPFER_HAS_OPTIONS=$?

# If there are any non-option arguments, send them to kupfer with PutText
# Grab text input either from command line or from stdin
if tty --quiet
then
	TEXT_INPUT="$*"
else
	echo "kupfer: Reading from stdin"
	TEXT_INPUT=$(cat)
fi


test $KUPFER_HAS_OPTIONS != 0 && dbus-send --print-reply --dest=se.kaizer.kupfer /interface se.kaizer.kupfer.Listener.Present >/dev/null 2>&1
KUPFER_RUNNING=$?

if test \( -n "$TEXT_INPUT" -a $KUPFER_HAS_OPTIONS != 0 \)
then
	dbus-send --print-reply --dest=se.kaizer.kupfer /interface \
	se.kaizer.kupfer.Listener.PutText string:"$PWD" string:"$TEXT_INPUT" \
	>/dev/null 2>&1
fi

if test $KUPFER_RUNNING != 0
then
	exec ${PYTHON} -m kupfer.__init__ $*
fi

${PYTHON} -c "import gtk.gdk; gtk.gdk.notify_startup_complete()"
