__kupfer_name__ = _("SSH Hosts")
__description__ = _("Adds the SSH hosts found in ~/.ssh/config.")
__version__ = "2010-04-12"
__author__ = "Fabian Carlström"

__kupfer_sources__ = ("SSHSource",)
__kupfer_actions__ = ("SSHConnect",)

import codecs
import os

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


class SSHLeaf(HostLeaf):
    """The SSH host. It only stores the "Host" as it was
    specified in the ssh config.
    """

    def __init__(self, name):
        slots = {
            HOST_NAME_KEY: name,
            HOST_ADDRESS_KEY: name,
            HOST_SERVICE_NAME_KEY: "ssh",
        }
        HostLeaf.__init__(self, slots, name)

    def get_description(self):
        return _("SSH host")

    def get_gicon(self):
        return icons.ComposedIconSmall(
            self.get_icon_name(), "applications-internet"
        )


class SSHConnect(Action):
    """Used to launch a terminal connecting to the specified
    SSH host.
    """

    def __init__(self):
        Action.__init__(self, name=_("Connect"))

    def activate(self, leaf, iobj=None, ctx=None):
        launch.spawn_in_terminal(["ssh", leaf[HOST_ADDRESS_KEY]])

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

    def get_items(self):
        try:
            with codecs.open(self._config_path, "r", "UTF-8") as cfile:
                for line in cfile.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    # Take every word after "Host" as an individual host
                    # we must skip entries with wildcards
                    head, *hosts = line.split()
                    if head and head.lower() == "host":
                        for host in hosts:
                            if "*" not in host:
                                yield SSHLeaf(host)

        except OSError as exc:
            self.output_error(exc)
        except UnicodeError as exc:
            self.output_error(
                f"File {self._config_path} not in expected encoding (UTF-8)"
            )
            self.output_error(exc)

    def get_description(self):
        return _("SSH hosts as specified in ~/.ssh/config")

    def get_icon_name(self):
        return "applications-internet"

    def provides(self):
        yield SSHLeaf
