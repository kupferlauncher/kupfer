"""
session sets up the program as a client to the current
desktop session and enables notifications on session
close, to be able to save state before being killed;

the module API does not depend on the session API used
"""

from __future__ import annotations

import os
import time
import typing as ty

import dbus
from gi.repository import GObject

from kupfer import version
from kupfer.support import pretty


class SessionClient(GObject.GObject, pretty.OutputMixin):  # type:ignore
    """Session handling controller

    signals:
    save-yourself: Program should save state
    die:           Program should quit immediately
    """

    __gtype_name__ = "SessionClient"

    def __init__(self):
        """Set up program as client to current Session"""
        GObject.GObject.__init__(self)
        self._session_ended = False
        self._client_id = None

        succ = False
        try:
            succ = self._connect_session_manager()
        except dbus.DBusException as exc:
            self.output_error(exc)

        if not succ:
            # try to bind to xfce session manager
            try:
                succ = self._connect_xfce_session_manager()
            except dbus.DBusException as exc:
                self.output_error(exc)

        self._enabled = succ or self._connect_gnomeui()

        # unset autostart id so that it is not transferred
        os.putenv("DESKTOP_AUTOSTART_ID", "")

        if not self.enabled:
            self.output_info(
                "Warning: Not able to connect to current "
                "desktop session, please Quit before logout to save "
                "kupfer's data."
            )

    def _connect_gnomeui(self) -> bool:
        return False

    def _connect_session_manager(self) -> bool:
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(
            "org.freedesktop.DBus", "/org/freedesktop/DBus"
        )
        dbus_iface = dbus.Interface(proxy_obj, "org.freedesktop.DBus")
        iface_name = service_name = "org.gnome.SessionManager"
        obj_name = "/org/gnome/SessionManager"

        if not dbus_iface.NameHasOwner(service_name):
            self.output_debug("D-Bus name", service_name, "not found")
            return False

        try:
            obj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as exc:
            pretty.print_error(__name__, exc)
            return False

        smanager = dbus.Interface(obj, iface_name)

        app_id = version.PACKAGE_NAME
        startup_id = os.getenv("DESKTOP_AUTOSTART_ID") or ""
        self._client_id = smanager.RegisterClient(app_id, startup_id)
        self._session_ended = False
        self.output_debug(
            "Connected to session as client", self._client_id, startup_id
        )

        private_iface_name = "org.gnome.SessionManager.ClientPrivate"
        bus.add_signal_receiver(
            self._on_query_end_session,
            "QueryEndSession",
            dbus_interface=private_iface_name,
        )
        bus.add_signal_receiver(
            self._on_end_session_signal,
            "EndSession",
            dbus_interface=private_iface_name,
        )
        bus.add_signal_receiver(
            self._on_stop_signal, "Stop", dbus_interface=private_iface_name
        )
        return True

    def _connect_xfce_session_manager(self) -> bool:
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object(
            "org.freedesktop.DBus", "/org/freedesktop/DBus"
        )
        dbus_iface = dbus.Interface(proxy_obj, "org.freedesktop.DBus")
        service_name = "org.xfce.SessionManager"
        obj_name = "/org/xfce/SessionManager"

        if not dbus_iface.NameHasOwner(service_name):
            self.output_debug("D-Bus name", service_name, "not found")
            return False

        try:
            bus.get_object(service_name, obj_name)
        except dbus.DBusException as exc:
            pretty.print_error(__name__, exc)
            return False

        private_iface_name = "org.xfce.Session.Manager"
        bus.add_signal_receiver(
            self._on_xfce_session_state_changed,
            "StateChanged",
            dbus_interface=private_iface_name,
        )
        return True

    def _get_response_obj(self) -> ty.Any:
        """Return D-Bus session object for ClientPrivate Interface"""
        service_name = "org.gnome.SessionManager"
        obj_name = self._client_id
        iface_name = "org.gnome.SessionManager.ClientPrivate"

        try:
            bus = dbus.Bus()
            obj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as exc:
            pretty.print_error(__name__, exc)
            return None

        return dbus.Interface(obj, iface_name)

    def _on_query_end_session(self, flags: str) -> None:
        self.output_debug("Query end", flags)

        if smanager := self._get_response_obj():
            smanager.EndSessionResponse(True, "Always OK")

    def _on_end_session_signal(self, flags: str) -> None:
        self.output_debug("Session end", flags)
        if not self._session_ended:
            self._session_ended = True
            self.emit("save-yourself")

        if smanager := self._get_response_obj():
            smanager.EndSessionResponse(True, "Always OK")

    def _on_xfce_session_state_changed(
        self, old_value: int, new_value: int
    ) -> None:
        self.output_debug(
            "XFCE Session change", time.asctime(), old_value, new_value
        )
        if new_value == 4:  # noqa:PLR2004
            self.emit("save-yourself")

    def _on_stop_signal(self) -> None:
        self.output_debug("Session stop")
        self.emit("die")

    # def _session_save(self, obj: ty.Any, *args: ty.Any) -> None:
    #     self.emit("save-yourself")

    # def _session_die(self, obj: ty.Any, *args: ty.Any) -> None:
    #     self.emit("die")

    @property
    def enabled(self) -> bool:
        """If a session connection is available"""
        return self._enabled


GObject.signal_new(
    "save-yourself",
    SessionClient,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
GObject.signal_new(
    "die",
    SessionClient,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
