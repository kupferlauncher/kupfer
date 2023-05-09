# pylint: disable=invalid-name
"""
This module has a singleton Service for dbus callbacks,
and ensures there is only one unique service in the Session
"""
from __future__ import annotations

import typing as ty

from gi.repository import GObject

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop

    DBusGMainLoop(set_as_default=True)
    import dbus.service
    from dbus.gi_service import ExportedGObject

    dbus.mainloop.glib.threads_init()

    # if dbus unavailable print the exception here
    # but further actions (register) will fail without warning
    _SESSION_BUS = dbus.Bus()
except (ImportError, dbus.exceptions.DBusException) as exc:
    _SESSION_BUS = None
    print(exc)

from kupfer.ui import uievents


class AlreadyRunningError(Exception):
    """Service already available on the bus Exception"""


class NoConnectionError(Exception):
    """Not possible to establish connection for callbacks"""


_SERVER_NAME: ty.Final = "se.kaizer.kupfer"
_INTERFACE_NAME: ty.Final = "se.kaizer.kupfer.Listener"
_OBJECT_NAME: ty.Final = "/interface"

_SERVER_NAME_NEW: ty.Final = "io.github.kupferlauncher"
_INTERFACE_NAME_NEW: ty.Final = "io.github.kupferlauncher.Listener"
_OBJECT_NAME_NEW: ty.Final = "/io/github/kupferlauncher"


class Service(ExportedGObject):  # type:ignore
    def __init__(self):
        """Create a new Kupfer service on the Session Bus

        Raises NoConnectionError, AlreadyRunningError
        """
        if not _SESSION_BUS:
            raise NoConnectionError

        if _SESSION_BUS.name_has_owner(_SERVER_NAME):
            raise AlreadyRunningError

        bus_name = dbus.service.BusName(_SERVER_NAME, bus=_SESSION_BUS)
        super().__init__(
            conn=_SESSION_BUS, object_path=_OBJECT_NAME, bus_name=bus_name
        )

    def unregister(self):
        if _SESSION_BUS:
            _SESSION_BUS.release_name(_SERVER_NAME)

    @dbus.service.method(_INTERFACE_NAME)
    def Present(self):
        self.PresentOnDisplay("", "")

    @dbus.service.method(_INTERFACE_NAME, in_signature="ay", byte_arrays=True)
    def PresentWithStartup(self, notify_id):
        self.PresentOnDisplay("", notify_id)

    @dbus.service.method(_INTERFACE_NAME, in_signature="ayay", byte_arrays=True)
    def PresentOnDisplay(self, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("present", display, time)

    @dbus.service.method(_INTERFACE_NAME)
    def ShowHide(self):
        self.emit("show-hide", "", 0)

    @dbus.service.method(_INTERFACE_NAME, in_signature="s")
    def PutText(self, text):
        self.PutTextOnDisplay(text, "", "")

    @dbus.service.method(
        _INTERFACE_NAME, in_signature="sayay", byte_arrays=True
    )
    def PutTextOnDisplay(self, text, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("put-text", text, display, time)

    @dbus.service.method(_INTERFACE_NAME, in_signature="as")
    def PutFiles(self, fileuris):
        self.PutFilesOnDisplay(fileuris, "", "")

    @dbus.service.method(
        _INTERFACE_NAME, in_signature="asayay", byte_arrays=True
    )
    def PutFilesOnDisplay(self, fileuris, display, notify_id):
        # files sent with dbus-send from kupfer have a custom comma
        # escape that we have to unescape here
        fileuris[:] = [f.replace("%%kupfercomma%%", ",") for f in fileuris]
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("put-files", fileuris, display, time)

    @dbus.service.method(_INTERFACE_NAME, in_signature="s")
    def ExecuteFile(self, filepath):
        self.ExecuteFileOnDisplay(filepath, "", "")

    @dbus.service.method(
        _INTERFACE_NAME, in_signature="sayay", byte_arrays=True
    )
    def ExecuteFileOnDisplay(self, filepath, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("execute-file", filepath, display, time)

    @dbus.service.method(
        _INTERFACE_NAME, in_signature="sayay", byte_arrays=True
    )
    def RelayKeysFromDisplay(self, keystring, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("relay-keys", keystring, display, time)

    @dbus.service.method(
        _INTERFACE_NAME,
        in_signature=None,
        out_signature="as",
        byte_arrays=True,
    )
    def GetBoundKeys(self):
        # pylint: disable=import-outside-toplevel
        from kupfer.ui import keybindings

        return keybindings.get_all_bound_keys()

    @dbus.service.signal(_INTERFACE_NAME, signature="sb")
    def BoundKeyChanged(self, keystr, is_bound):
        pass

    @dbus.service.method(_INTERFACE_NAME)
    def Quit(self):
        self.emit("quit")


# Signature: displayname, timestamp
GObject.signal_new(
    "present",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: displayname, timestamp
GObject.signal_new(
    "show-hide",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: text, displayname, timestamp
GObject.signal_new(
    "put-text",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: filearray, displayname, timestamp
GObject.signal_new(
    "put-files",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: fileuri, displayname, timestamp
GObject.signal_new(
    "execute-file",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: ()
GObject.signal_new(
    "quit", Service, GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ()
)

# Signature: keystring, displayname, timestamp
GObject.signal_new(
    "relay-keys",
    Service,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)


class ServiceNew(ExportedGObject):  # type: ignore
    def __init__(self):
        """Create a new Kupfer service on the Session Bus

        Raises NoConnectionError, AlreadyRunningError
        """
        if not _SESSION_BUS:
            raise NoConnectionError

        if _SESSION_BUS.name_has_owner(_SERVER_NAME_NEW):
            raise AlreadyRunningError

        bus_name = dbus.service.BusName(_SERVER_NAME_NEW, bus=_SESSION_BUS)
        super().__init__(
            conn=_SESSION_BUS, object_path=_OBJECT_NAME_NEW, bus_name=bus_name
        )

    def unregister(self):
        if _SESSION_BUS:
            _SESSION_BUS.release_name(_SERVER_NAME)

    @dbus.service.method(_INTERFACE_NAME_NEW)
    def Present(self):
        self.PresentOnDisplay("", "")

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="ss")
    def PresentOnDisplay(self, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("present", display, time)

    @dbus.service.method(_INTERFACE_NAME_NEW)
    def ShowHide(self):
        self.ShowHideOnDisplay("", "")

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="ss")
    def ShowHideOnDisplay(self, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("show-hide", display, time)

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="s")
    def PutText(self, text):
        self.PutTextOnDisplay(text, "", "")

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="sss")
    def PutTextOnDisplay(self, text, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("put-text", text, display, time)

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="as")
    def PutFiles(self, fileuris):
        self.PutFilesOnDisplay(fileuris, "", "")

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="asss")
    def PutFilesOnDisplay(self, fileuris, display, notify_id):
        # files sent with dbus-send from kupfer have a custom comma
        # escape that we have to unescape here
        fileuris[:] = [f.replace("%%kupfercomma%%", ",") for f in fileuris]
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("put-files", fileuris, display, time)

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="s")
    def ExecuteFile(self, filepath):
        self.ExecuteFileOnDisplay(filepath, "", "")

    @dbus.service.method(_INTERFACE_NAME_NEW, in_signature="sss")
    def ExecuteFileOnDisplay(self, filepath, display, notify_id):
        with uievents.using_startup_notify_id(notify_id) as time:
            self.emit("execute-file", filepath, display, time)

    @dbus.service.method(_INTERFACE_NAME_NEW)
    def Quit(self):
        self.emit("quit")


# Signature: displayname, timestamp
GObject.signal_new(
    "present",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: displayname, timestamp
GObject.signal_new(
    "show-hide",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: text, displayname, timestamp
GObject.signal_new(
    "put-text",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: filearray, displayname, timestamp
GObject.signal_new(
    "put-files",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: fileuri, displayname, timestamp
GObject.signal_new(
    "execute-file",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)

# Signature: ()
GObject.signal_new(
    "quit", ServiceNew, GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ()
)


# Note ServiceNew has the same signals, but doesn't actually implement them
# all (yet). Needs new design for wayland keyrelay.
# Signature: keystring, displayname, timestamp
GObject.signal_new(
    "relay-keys",
    ServiceNew,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_UINT),
)
