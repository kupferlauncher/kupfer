#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2022 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Plugin allow control domains (virtual machines) managed by libvirt.
"""

__kupfer_name__ = _("libvirt")
__kupfer_sources__ = ("LibvirtDomainsSource",)
__description__ = _("Control libvirt guest domains.")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import libvirt

from kupfer import utils
from kupfer.objects import Leaf, Action, Source
from kupfer import plugin_support
from kupfer.obj.apps import AppLeafContentMixin

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
        with libvirt.openReadOnly(
            __kupfer_settings__["connection"] or None
        ) as conn:
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


class LibvirtDomainsSource(AppLeafContentMixin, Source):
    source_use_cache = False
    appleaf_content_id = "virt-manager"

    def initialize(self):
        # prevent logging errors from libvirt
        libvirt.registerErrorHandler(lambda userdata, err: None, ctx=None)

    def __init__(self, name=_("Libvirt domains")):
        Source.__init__(self, name)

    def is_dynamic(self):
        return True

    def get_items(self):
        with libvirt.openReadOnly(
            __kupfer_settings__["connection"] or None
        ) as conn:
            for dom in conn.listAllDomains():
                name = dom.name()
                title = _get_domain_metadata(
                    dom, libvirt.VIR_DOMAIN_METADATA_TITLE
                )
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
        utils.spawn_async(
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
