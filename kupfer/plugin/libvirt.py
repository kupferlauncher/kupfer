# Copyright © 2022 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Plugin allow control domains (virtual machines) managed by libvirt.
"""
from __future__ import annotations

__kupfer_name__ = _("Libvirt")
__kupfer_sources__ = ("LibvirtDomainsSource",)
__description__ = _("Control libvirt guest domains.")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import threading
import typing as ty

import libvirt

from kupfer import launch, plugin_support, icons
from kupfer.obj import Action, Leaf, Source
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.support import pretty

if ty.TYPE_CHECKING:
    from gettext import gettext as _


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "connection",
        "label": _("Connection"),
        "type": str,
        "value": "qemu:///system",
    },
)


class Domain(Leaf):
    def __init__(self, obj, name, description):
        Leaf.__init__(self, obj, name)
        self.description = description

    def get_description(self):
        return self.description

    def get_actions(self):
        conn = _ConnManager.instance().get_conn()
        if not conn:
            return

        domain = conn.lookupByName(self.object)
        state, _reason = domain.state()

        # https://libvirt.org/html/libvirt-libvirt-domain.html#virDomainState
        if state == libvirt.VIR_DOMAIN_RUNNING:
            yield DomAction(_("Pause"), "pause", "pause")
            yield DomAction(_("Reboot"), "system-reboot", "reboot", -5)
            yield DomAction(
                _("Send Power Off Signal"),
                "system-shutdown",
                "poweroff-signal",
                -10,
            )
            yield DomAction(_("Power Off"), "system-shutdown", "poweroff", -15)
        elif state in (
            libvirt.VIR_DOMAIN_PAUSED,
            libvirt.VIR_DOMAIN_PMSUSPENDED,
        ):
            yield DomAction(_("Resume"), "system-run", "resume")
        elif state in (
            libvirt.VIR_DOMAIN_BLOCKED,
            libvirt.VIR_DOMAIN_SHUTDOWN,
        ):
            pass
        else:  # libvirt.VIR_DOMAIN_SHUTOFF:
            yield DomAction(_("Power On"), "system-run", "start")

        yield OpenConsoleAction()

    def get_gicon(self):
        return icons.ComposedIconSmall("computer", "virt-manager")


class DomAction(Action):
    def __init__(self, name, icon, command, rank_adjust=0):
        Action.__init__(self, name)
        self._icon = icon
        self.rank_adjust = rank_adjust
        self.command = command

    def get_icon_name(self):
        return self._icon

    def item_types(self):
        yield Domain

    def activate(self, leaf, iobj=None, ctx=None):
        with libvirt.open(__kupfer_settings__["connection"] or None) as conn:
            domain = conn.lookupByName(leaf.object)

            if self.command == "poweroff":
                domain.shutdown()
            elif self.command == "pause":
                domain.suspend()
            elif self.command == "reboot":
                domain.reboot(libvirt.VIR_DOMAIN_REBOOT_DEFAULT)
            elif self.command == "resume":
                domain.resume()
            elif self.command == "start":
                domain.create()
            elif self.command == "poweroff-signal":
                domain.shutdownFlags(libvirt.VIR_DOMAIN_SHUTDOWN_DEFAULT)


def _get_domain_metadata(domain, key):
    try:
        return domain.metadata(key, None)
    except libvirt.libvirtError:
        pass
    return None


class _ConnManager(pretty.OutputMixin):
    """Libvirt connection manager. Only for read-only connections."""

    _instance: _ConnManager | None = None

    @classmethod
    def instance(cls) -> _ConnManager:
        if not cls._instance:
            cls._instance = _ConnManager()

        return cls._instance

    def __init__(self):
        self.conn: libvirt.virConnect | None = None
        self._start_event_loop()
        __kupfer_settings__.connect(
            "plugin-setting-changed", self._on_setting_changed
        )

    def _event_loop(self) -> None:
        while True:
            libvirt.virEventRunDefaultImpl()

    def _start_event_loop(self) -> None:
        libvirt.virEventRegisterDefaultImpl()
        thr = threading.Thread(
            target=self._event_loop, name="libvirtEventLoop", daemon=True
        )
        thr.start()

    def _open(self) -> None:
        connstr = __kupfer_settings__["connection"] or None
        self.output_debug("LibVirt Connection open", connstr)
        self.conn = libvirt.openReadOnly(connstr)
        if self.conn:
            self.conn.setKeepAlive(5, 3)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _on_setting_changed(self, settings, key, value):
        if self.conn:
            self.conn.close()
            self._open()

    def get_conn(self) -> libvirt.virConnect | None:
        if self.conn is None:
            self._open()

        return self.conn


class LibvirtDomainsSource(AppLeafContentMixin, Source):
    source_use_cache = False
    appleaf_content_id = "virt-manager"

    def __init__(self, name=_("Libvirt domains")):
        Source.__init__(self, name)
        self.cmgr: _ConnManager | None = None

    def initialize(self):
        # prevent logging errors from libvirt
        libvirt.registerErrorHandler(lambda userdata, err: None, ctx=None)
        self.cmgr = _ConnManager.instance()
        if conn := self.cmgr.get_conn():
            conn.domainEventRegister(self._callback, None)

    def finalize(self):
        if self.cmgr:
            self.cmgr.close()
            self.cmgr = None

    def _callback(self, _conn, dom, event, detail, _opaque):
        pretty.print_debug(
            "LibvirtDomainsSource event", dom.name(), dom.ID(), event, detail
        )
        self.mark_for_update()

    def get_items(self):
        assert self.cmgr
        conn = self.cmgr.get_conn()
        if not conn:
            return

        for dom in conn.listAllDomains():
            name = dom.name()
            title = _get_domain_metadata(dom, libvirt.VIR_DOMAIN_METADATA_TITLE)
            descr = _get_domain_metadata(
                dom, libvirt.VIR_DOMAIN_METADATA_DESCRIPTION
            )
            yield Domain(name, title or name, descr)

    def get_description(self):
        return None

    def provides(self):
        yield Domain

    def should_sort_lexically(self):
        return True


class OpenConsoleAction(Action):
    def __init__(self):
        Action.__init__(self, name=_("Open console"))

    def get_icon_name(self):
        return "virt-manager"

    def item_types(self):
        yield Domain

    def activate(self, leaf, iobj=None, ctx=None):
        conn = __kupfer_settings__["connection"] or "qemu:///system"
        domain = leaf.object
        launch.spawn_async(
            [
                "virt-manager",
                "--connect",
                conn,
                "--show-domain-console",
                domain,
            ]
        )

    def get_description(self):
        return _("Open Virtual Machine Manager console for domain")
