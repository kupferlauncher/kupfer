from __future__ import annotations

__kupfer_name__ = _("SSH Hosts")
__description__ = _("Adds the SSH hosts found in ~/.ssh/config.")
__version__ = "2010-04-12"
__author__ = "Fabian Carlström"

__kupfer_sources__ = ("SSHSource",)
__kupfer_actions__ = ("SSHConnect",)

import os
import typing as ty

from kupfer import icons, launch
from kupfer.obj import Action
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.hosts import (
    HOST_ADDRESS_KEY,
    HOST_NAME_KEY,
    HOST_SERVICE_NAME_KEY,
    HostLeaf,
)

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class SSHLeaf(HostLeaf):
    """The SSH host. It only stores the "Host" as it was specified in the ssh
    config.
    By default name is set as hostname.
    """

    def __init__(self, name: str, hostname: str | None = None) -> None:
        hostname = hostname or name
        slots = {
            HOST_NAME_KEY: name,
            HOST_ADDRESS_KEY: hostname,
            HOST_SERVICE_NAME_KEY: "ssh",
        }
        HostLeaf.__init__(self, slots, name)

    def get_description(self) -> str:
        return _("SSH host: %s") % self[HOST_ADDRESS_KEY]

    def get_gicon(self):
        return icons.ComposedIconSmall(
            self.get_icon_name(), "applications-internet"
        )


class SSHConnect(Action):
    """Used to launch a terminal connecting to the specified SSH host.
    HOST_NAME_KEY is used for making connections.
    """

    def __init__(self):
        Action.__init__(self, name=_("Connect"))

    def activate(self, leaf, iobj=None, ctx=None):
        launch.spawn_in_terminal(["ssh", leaf[HOST_NAME_KEY]])

    def get_description(self):
        return _("Connect to SSH host")

    def get_icon_name(self):
        return "network-server"

    def item_types(self):
        yield HostLeaf

    def valid_for_item(self, leaf):
        if leaf.check_key(HOST_SERVICE_NAME_KEY):
            return leaf[HOST_SERVICE_NAME_KEY] == "ssh"

        return False


class SSHSource(ToplevelGroupingSource, FilesystemWatchMixin):
    """Reads ~/.ssh/config and creates leaves for the hosts found."""

    source_scan_interval: int = 3600

    _ssh_home = os.path.expanduser("~/.ssh")
    _ssh_config_file = "config"
    _config_path = os.path.join(_ssh_home, _ssh_config_file)

    def __init__(self, name=_("SSH Hosts")):
        ToplevelGroupingSource.__init__(self, name, "hosts")
        self._version = 2
        self.monitor_token = None

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        self.monitor_token = self.monitor_directories(
            self._ssh_home, force=True
        )

    def monitor_include_file(self, gfile):
        return gfile and gfile.get_path() in (
            self._ssh_config_file,
            self._ssh_home,
        )

    def _get_items(self) -> ty.Iterable[SSHLeaf]:
        with open(self._config_path, encoding="UTF-8") as cfile:
            current_hosts: list[str] = []
            for line in cfile.readlines():
                line = line.strip()
                if not line:
                    continue

                head, *args = line.split()
                head = head.lower()
                if head in ("host", "match"):
                    # new restriction, flush current data
                    if current_hosts:
                        yield from map(SSHLeaf, current_hosts)

                    current_hosts.clear()
                    if head == "host":
                        # process only 'host' restriction; skip wildcard and
                        # negative entries
                        current_hosts = [
                            host
                            for host in args
                            if "*" not in host and host[0] != "!"
                        ]

                elif head == "hostname" and args:
                    # if found hostname use is as HOST_ADDRESS_KEY
                    hostname = args[0]
                    if current_hosts:
                        yield from (
                            SSHLeaf(host, hostname) for host in current_hosts
                        )
                        current_hosts.clear()

            if current_hosts:
                yield from map(SSHLeaf, current_hosts)

    def get_items(self):
        try:
            return list(self._get_items())
        except OSError as exc:
            self.output_error(exc)
        except UnicodeError as exc:
            self.output_error(
                f"File {self._config_path} not in expected encoding (UTF-8)"
            )
            self.output_error(exc)

        return ()

    def get_description(self):
        return _("SSH hosts as specified in ~/.ssh/config")

    def get_icon_name(self):
        return "applications-internet"

    def provides(self):
        yield SSHLeaf
