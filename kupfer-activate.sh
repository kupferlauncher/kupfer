#!/bin/sh

# Try to spawn kupfer via dbus, else go to python
dbus-send --print-reply --dest=se.kaizer.kupfer /interface se.kaizer.kupfer.Listener.ShowHide >/dev/null 2>&1

test $? != 0 && python -m kupfer $*
