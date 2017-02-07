"""
session sets up the program as a client to the current
desktop session and enables notifications on session
close, to be able to save state before being killed;

the module API does not depend on the session API used
"""

import os
import time

from gi.repository import GObject
import dbus

from kupfer import pretty, version

class SessionClient (GObject.GObject, pretty.OutputMixin):
    """Session handling controller

    signals:
    save-yourself: Program should save state
    die:           Program should quit immediately
    """
    __gtype_name__ = "SessionClient"

    def __init__(self):
        """Set up program as client to current Session"""
        GObject.GObject.__init__(self)

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
        if not succ:
            succ = self._connect_gnomeui()

        # unset autostart id so that it is not transferred
        os.putenv("DESKTOP_AUTOSTART_ID", "")
        self._enabled = succ
        if not self.enabled:
            self.output_info("Warning: Not able to connect to current "
                "desktop session, please Quit before logout to save "
                "kupfer's data.")

    def _connect_gnomeui(self):
        return False

    def _connect_session_manager(self):
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        service_name = "org.gnome.SessionManager"
        obj_name = "/org/gnome/SessionManager"
        iface_name = service_name

        if not dbus_iface.NameHasOwner(service_name):
            self.output_debug("D-Bus name %s not found" % service_name)
            return False

        try:
            obj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as e:
            pretty.print_error(__name__, e)
            return False
        smanager = dbus.Interface(obj, iface_name)

        app_id = version.PACKAGE_NAME
        startup_id = os.getenv("DESKTOP_AUTOSTART_ID") or ""
        self.client_id = smanager.RegisterClient(app_id, startup_id)
        self._session_ended = False
        self.output_debug("Connected to session as client",
                self.client_id, startup_id)

        private_iface_name = "org.gnome.SessionManager.ClientPrivate"
        bus.add_signal_receiver(self._query_end_session, "QueryEndSession",
                dbus_interface=private_iface_name)
        bus.add_signal_receiver(self._end_session_signal, "EndSession",
                dbus_interface=private_iface_name)
        bus.add_signal_receiver(self._stop_signal, "Stop",
                dbus_interface=private_iface_name)
        return True

    def _connect_xfce_session_manager(self):
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object('org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
        service_name = "org.xfce.SessionManager"
        obj_name = "/org/xfce/SessionManager"

        if not dbus_iface.NameHasOwner(service_name):
            self.output_debug("D-Bus name %s not found" % service_name)
            return False

        try:
            bus.get_object(service_name, obj_name)
        except dbus.DBusException as e:
            pretty.print_error(__name__, e)
            return False

        private_iface_name = "org.xfce.Session.Manager"
        bus.add_signal_receiver(self._xfce_session_state_changed, "StateChanged",
                dbus_interface=private_iface_name)
        return True

    def _get_response_obj(self):
        """Return D-Bus session object for ClientPrivate Interface"""
        service_name = "org.gnome.SessionManager"
        obj_name = self.client_id
        iface_name = "org.gnome.SessionManager.ClientPrivate"

        try:
            bus = dbus.Bus()
            obj = bus.get_object(service_name, obj_name)
        except dbus.DBusException as e:
            pretty.print_error(__name__, e)
            return None
        smanager = dbus.Interface(obj, iface_name)
        return smanager

    def _query_end_session(self, flags):
        self.output_debug("Query end", flags)

        smanager = self._get_response_obj()
        smanager and smanager.EndSessionResponse(True, "Always OK")

    def _end_session_signal(self, flags):
        self.output_debug("Session end", flags)
        if not self._session_ended:
            self._session_ended = True
            self.emit("save-yourself")
        smanager = self._get_response_obj()
        smanager and smanager.EndSessionResponse(True, "Always OK")

    def _xfce_session_state_changed(self, old_value, new_value):
        self.output_debug("XFCE Session change", time.asctime(),
                old_value, new_value)
        if new_value == 4:
            self.emit("save-yourself")

    def _stop_signal(self):
        self.output_debug("Session stop")
        self.emit("die")
    def _session_save(self, obj, *args):
        self.emit("save-yourself")
    def _session_die(self, obj, *args):
        self.emit("die")
    @property
    def enabled(self):
        """If a session connection is available"""
        return self._enabled

GObject.signal_new("save-yourself", SessionClient, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
GObject.signal_new("die", SessionClient, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
