# -*- coding: UTF-8 -*-
__kupfer_name__ = _("System Services")
__kupfer_sources__ = ("SystemServicesSource", )
__description__ = _("Start, stop or restart system services via init scripts")
__version__ = "0.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os

from kupfer import plugin_support
from kupfer.objects import Leaf, Action, Source 
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer import utils

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        'key': 'sudo_cmd',
        'label': _("Sudo-like Command"),
        'type': str,
        'value': 'gksu',
    },
)


# skip this services
_SERVICES_BLACK_LIST = [
        "acpid", "acpi-support", "alsa-utils", "apmd", "binfmt-support",
        "bootlogd", "bootmisc.sh", "checkfs.sh", "checkroot.sh",
        "console-screen.kbd.sh", "console-setup", "dbus", "dns-clean", "glibc.sh", 
        "hal", "halt", "hostname.sh", "hotkey-setup", "hwclockfirst.sh", 
        "hwclock.sh", "keyboard-setup", "killprocs", "klogd", "laptop-mode", 
        "linux-restricted-modules-common", "module-init-tools", 
        "mountall-bootclean.sh", "mountall.sh", "mountdevsubfs.sh", "mountkernfs.sh", 
        "mountnfs-bootclean.sh", "mountnfs.sh", "mountoverflowtmp", "mtab.sh",
        "policykit", "pppd-dns", "procps", "rc", "rc.local", "rcS", "reboot",   
        "readahead", "readahead-desktop", "rmnologin", "screen-cleanup", "sendsigs", 
        "single", "stop-bootlogd", "stop-bootlogd-single", "stop-readahead",
        "sysklogd", "system-tools-backends", "udev", "udev-finish", "umountfs", 
        "umountnfs.sh", "umountroot", "urandom", "vbesave", "wpa-ifupdown", "x11-common", 
        'README'
]


class Service(Leaf):
    """ Represent system service """
    def get_actions(self):
        yield StartService()
        yield StopService()
        yield RestartService()

    def get_description(self):
        return self.object

    def get_icon_name(self):
        return "applications-system"


class _ServiceAction(Action):
    def __init__(self, name, icon, command):
        Action.__init__(self, name)
        self._icon = icon
        self._command = command

    def get_icon_name(self):
        return self._icon

    def activate(self, leaf):
        sudo_cmd = __kupfer_settings__["sudo_cmd"]
        utils.spawn_in_terminal([sudo_cmd, leaf.object, self._command])

    def item_types(self):
        yield Service


class StartService(_ServiceAction):
    """ Start service action """
    def __init__(self):
        _ServiceAction.__init__(self, _('Start Service'), 'start', 'start')


class RestartService(_ServiceAction):
    """ restart service action """
    def __init__(self):
        _ServiceAction.__init__(self, _('Restart Service'), 'reload', 'restart')


class StopService(_ServiceAction):
    """ restart service action """
    def __init__(self):
        _ServiceAction.__init__(self, _('Stop Service'), 'stop', 'stop')


class SystemServicesSource(Source, FilesystemWatchMixin):
    ''' Index system services from /etc/*/init.d/ '''

    def __init__(self, name=_("System Services")):
        Source.__init__(self, name)
        self._initd_path = None

    def initialize(self):
        # path to file with list notebooks
        for initd_path in ('/etc/init.d/', '/etc/rc.d/init.d', '/etc/rc.d'):
            if os.path.exists(initd_path) and os.path.isdir(initd_path):
                self._initd_path = initd_path
                self.monitor_token = self.monitor_directories(self._initd_path)
                break


    def monitor_include_file(self, gfile):
        return gfile and not gfile.get_basename() in _SERVICES_BLACK_LIST

    def get_items(self):
        if self._initd_path is None:
            return

        for filename in os.listdir(self._initd_path):
            if (filename in _SERVICES_BLACK_LIST \
                    or filename.find('dpkg-') > 0 or filename.endswith('~') \
                    or filename.startswith('.')):
                continue

            file_path = os.path.join(self._initd_path, filename)
            if not os.path.isfile(file_path):
                continue

            yield Service(file_path, _("%s Service") % filename)

    def should_sort_lexically(self):
        return True

    def get_icon_name(self):
        return "applications-system"

    def provides(self):
        yield Service

