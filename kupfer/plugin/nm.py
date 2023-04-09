"""
Network Manager plugin.
"""
from __future__ import annotations

__kupfer_name__ = _("NetworkManager")
__kupfer_sources__ = ("DevicesSource",)
__kupfer_actions__ = ("ToggleWireless",)
__description__ = _("Manage NetworkManager connections")
__version__ = "2023.01"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import time
import typing as ty

import dbus

from kupfer import icons, plugin_support
from kupfer.obj import Action, Leaf, NotAvailableError, Source
from kupfer.support import pretty, weaklib
from kupfer.ui import uiutils

plugin_support.check_dbus_connection()

if ty.TYPE_CHECKING:
    _ = str

_NM_SERVICE = "org.freedesktop.NetworkManager"
_NM_OBJECT = "/org/freedesktop/NetworkManager"
_NM_IFACE = "org.freedesktop.NetworkManager"

_DEVICE_IFACE = "org.freedesktop.NetworkManager.Device"
_PROPS_IFACE = "org.freedesktop.DBus.Properties"
_CONNECTION_IFACE = "org.freedesktop.NetworkManager.Settings.Connection"

_SETTINGS_OBJECT = "/org/freedesktop/NetworkManager/Settings"
_SETTINGS_IFACE = "org.freedesktop.NetworkManager.Settings"


def _create_dbus_connection(iface, obj, service, /, sbus=None):
    """Create dbus connection to NetworkManager"""
    try:
        sbus = sbus or dbus.SystemBus()
        if dobj := sbus.get_object(service, obj):
            return dbus.Interface(dobj, iface)

    except dbus.exceptions.DBusException as err:
        pretty.print_debug(__name__, err)

    raise NotAvailableError(_("NetworkManager"))


def _create_dbus_connection_nm(sbus=None):
    return _create_dbus_connection(
        _NM_IFACE, _NM_OBJECT, _NM_SERVICE, sbus=sbus
    )


def _create_dbus_connection_device(obj, /, sbus=None):
    return _create_dbus_connection(_DEVICE_IFACE, obj, _NM_SERVICE, sbus=sbus)


_NM_DEVICE_STATE = {
    # TRANS: network device status
    0: _("unknown"),
    # TRANS: network device status
    10: _("unmanaged"),
    # TRANS: network device status
    20: _("unavailable"),
    # TRANS: network device status
    30: _("disconnected"),
    # TRANS: network device status
    40: _("prepare"),
    # TRANS: network device status
    50: _("config"),
    # TRANS: network device status
    60: _("need auth"),
    # TRANS: network device status
    70: _("ip config"),
    # TRANS: network device status
    80: _("ip check"),
    # TRANS: network device status
    90: _("secondaries"),
    # TRANS: network device status
    100: _("activated"),
    # TRANS: network device status
    110: _("deactivating"),
    # TRANS: network device status
    120: _("failed"),
}

_NM_DEVICE_TYPES = {
    0: "unknown",
    1: "ethernet",
    2: "wifi",
    3: "unused1",
    4: "unused2",
    5: "bt",
    6: "olpc mesh",
    7: "wimax",
    8: "modem",
    9: "infiniband",
    10: "bond",
    11: "vlan",
    12: "adsl",
    13: "bridge",
    14: "generic",
    15: "team",
    16: "tun",
    17: "ip tunnel",
    18: "macvlan",
    19: "vxlan",
    20: "veth",
    21: "macsec",
    22: "dummy",
    23: "ppp",
    24: "ovs interface",
    25: "ovs port",
    26: "ovs bridge",
    27: "wpan",
    28: "6lowpan",
    29: "wireguard",
    30: "wifi_p2p",
    31: "vrf",
}


class Device(Leaf):
    def __init__(
        self, path: str, name: str, status: int, managed: bool, devtype: int
    ):
        Leaf.__init__(self, path, name)
        self._status = status
        self.managed = managed
        self.devtype = devtype

    def get_description(self):
        return _("Network device %(dtype)s; state: %(state)s") % {
            "dtype": _NM_DEVICE_TYPES.get(self.devtype) or "unknown",
            "state": _NM_DEVICE_STATE.get(self._status) or str(self._status),
        }

    def get_icon_name(self):
        if self.devtype == 2:
            return "network-wireless"

        if self.devtype == 29:
            return "network-vpn"

        return "network-wired"

    def get_actions(self):
        yield Disconnect()
        yield Connect()
        yield ShowInfo()

    def status(self) -> int:
        conn = _create_dbus_connection(_PROPS_IFACE, self.object, _NM_SERVICE)
        self._status = int(conn.Get(_DEVICE_IFACE, "State"))
        return self._status


class Disconnect(Action):
    def __init__(self):
        Action.__init__(self, _("Disconnect"))

    def activate(self, leaf, iobj=None, ctx=None):
        bus = dbus.SystemBus()
        try:
            interface = _create_dbus_connection_device(leaf.object, sbus=bus)
            interface.Disconnect()
            time.sleep(1)
        except Exception:
            pretty.print_exc(__name__)

        # return leaf with updated status
        leaf.status()
        return leaf

    def get_icon_name(self):
        return "disconnect"

    def get_description(self):
        return _("Disconnect connection")

    def valid_for_item(self, leaf):
        return leaf.status() == 100

    def has_result(self):
        return True


class Connect(Action):
    def __init__(self):
        # TRANS: activate connection (connect)
        Action.__init__(self, _("Connect..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj

        bus = dbus.SystemBus()
        try:
            interface = _create_dbus_connection_nm(sbus=bus)
            interface.ActivateConnection(iobj.object, leaf.object, "/")
            time.sleep(1)
        except Exception:
            pretty.print_exc(__name__)

        leaf.status()
        return leaf

    def get_description(self):
        return _("Activate connection")

    def get_icon_name(self):
        return "connect"

    def requires_object(self):
        return True

    def object_types(self):
        yield Connection

    def object_source(self, for_item=None):
        return ConnectionsSource(for_item.object, for_item.name)

    def valid_for_item(self, leaf):
        return leaf.status() != 100

    def has_result(self):
        return True


def _get_info_recursive(item, level=0):
    prefix = "    " * level
    if isinstance(item, (dict, dbus.Dictionary)):
        for key, val in item.items():
            yield (f"{prefix}{key}:")
            yield from _get_info_recursive(val, level + 1)

    elif isinstance(item, (tuple, list, dbus.Array)):
        for val in item:
            yield from _get_info_recursive(val)

    elif level > 0:
        # skip garbage on first level
        yield (f"{prefix}{item}")


class ShowInfo(Action):
    def __init__(self):
        Action.__init__(self, _("Show informations"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        conn_info = ""
        props_info = ""
        bus = dbus.SystemBus()
        try:
            interface = _create_dbus_connection_device(leaf.object, sbus=bus)
            info = interface.GetAppliedConnection(0)
        except Exception as err:
            conn_info = f"Error: {err}"
        else:
            conn_info = "\n".join(_get_info_recursive(info))

        try:
            interface = _create_dbus_connection(
                _PROPS_IFACE, leaf.object, _NM_SERVICE, sbus=bus
            )
            props = interface.GetAll(_DEVICE_IFACE)
        except Exception as err:
            props_info = f"Error: {err}"
        else:
            props_info = "\n".join(_get_info_recursive(props))

        msg = f"DEVICE\n{props_info}\n------------\n\nCONNECTION\n{conn_info}"
        uiutils.show_text_result(msg, title=_("Connection details"), ctx=ctx)

    def get_description(self):
        return _("Show informations about device")


class Connection(Leaf):
    def __init__(self, path: str, name: str, descr: str):
        Leaf.__init__(self, path, name)
        self.descr = descr

    def get_description(self):
        return self.descr

    @staticmethod
    def from_setting(conn: str, settings: dict[str, ty.Any]) -> Connection:
        conn_id = str(settings["id"])
        conn_type = str(settings["type"])
        return Connection(conn, conn_id, conn_type)


class ConnectionsSource(Source):
    source_use_cache = False

    def __init__(self, device_path, interface):
        super().__init__(_("Connections"))
        self.device = device_path
        self.interface = interface

    def get_items(self):
        sbus = dbus.SystemBus()
        dconn = _create_dbus_connection(
            _PROPS_IFACE, self.device, _NM_SERVICE, sbus=sbus
        )
        if not dconn:
            return

        # get available connection for device
        need_check_conn = False
        connections = dconn.Get(_DEVICE_IFACE, "AvailableConnections")
        if not connections:
            # no connections for given device, check all
            dconn = _create_dbus_connection(
                _SETTINGS_IFACE, _SETTINGS_OBJECT, _NM_SERVICE, sbus=sbus
            )
            if not dconn:
                return

            need_check_conn = True
            connections = dconn.ListConnections()

        for conn in connections:
            cset = _create_dbus_connection(
                _CONNECTION_IFACE, conn, _NM_SERVICE, sbus=sbus
            )
            settings = cset.GetSettings()
            settings_connection = settings.get("connection")
            if need_check_conn:
                iface_name = str(settings_connection.get("interface-name"))
                if iface_name != self.interface:
                    continue

            yield Connection.from_setting(conn, settings_connection)


class DevicesSource(Source):
    def __init__(self, name=None):
        Source.__init__(self, name or __kupfer_name__)

    def initialize(self):
        bus = dbus.SystemBus()
        weaklib.dbus_signal_connect_weakly(
            bus,
            "StateChanged",
            self._on_nm_updated,
            dbus_interface=_NM_IFACE,
        )
        weaklib.dbus_signal_connect_weakly(
            bus,
            "DeviceAdded",
            self._on_nm_updated,
            dbus_interface=_NM_IFACE,
        )
        weaklib.dbus_signal_connect_weakly(
            bus,
            "DeviceRemoved",
            self._on_nm_updated,
            dbus_interface=_NM_IFACE,
        )

    def _on_nm_updated(self, *args):
        self.mark_for_update()

    def get_items(self):
        sbus = dbus.SystemBus()
        if interface := _create_dbus_connection_nm(sbus=sbus):
            for dev in interface.GetAllDevices():
                if conn := _create_dbus_connection(
                    _PROPS_IFACE, dev, _NM_SERVICE, sbus=sbus
                ):
                    yield Device(
                        str(dev),
                        str(conn.Get(_DEVICE_IFACE, "Interface")),
                        int(conn.Get(_DEVICE_IFACE, "State")),
                        bool(conn.Get(_DEVICE_IFACE, "Managed")),
                        int(conn.Get(_DEVICE_IFACE, "DeviceType")),
                    )

    def provides(self):
        yield Device

    def get_icon_name(self):
        return "network-wired"


class ToggleWireless(Action):
    def __init__(self):
        Action.__init__(self, "Toggle wireless")

    def _activate(self, sbus: dbus.Bus) -> str | None:
        if interface := _create_dbus_connection(
            _PROPS_IFACE, _NM_OBJECT, _NM_SERVICE, sbus=sbus
        ):
            if not bool(interface.Get(_NM_IFACE, "WirelessHardwareEnabled")):
                # TRANS: notification text when wireless is disabled by hardware
                return _("Hardware wireless disabled")

            state = not bool(interface.Get(_NM_IFACE, "WirelessEnabled"))
            interface.Set(_NM_IFACE, "WirelessEnabled", state)
            if state:
                # TRANS: notification text after wireless enabled
                return _("Wireless enabled")

            # TRANS: notification text after wireless disabled
            return _("Wireless disabled")

        return None

    def activate(self, leaf, iobj=None, ctx=None):
        sbus = dbus.SystemBus()
        if msg := self._activate(sbus):
            uiutils.show_notification("Kupfer", msg)

    def get_description(self):
        return "Toggle wireless by NetworkManager"

    def get_gicon(self):
        return icons.ComposedIcon("network-wireless", "emblem-system")

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf: Leaf) -> bool:
        return bool(leaf.object) and isinstance(leaf.object, DevicesSource)
