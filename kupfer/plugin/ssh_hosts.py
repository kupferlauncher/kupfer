from __future__ import annotations

__kupfer_name__ = _("SSH Hosts")
__description__ = _("Adds the SSH hosts found in ~/.ssh/config.")
__version__ = "2023-11-04"
__author__ = "Fabian Carlström, Karol Będkowski"

__kupfer_sources__ = ("SSHSource",)
__kupfer_actions__ = ("SSHConnect", "ScpFile")

import itertools
import os
import typing as ty
from contextlib import suppress

from kupfer import icons, launch
from kupfer.obj import Action, FileLeaf
from kupfer.obj.grouping import ToplevelGroupingSource
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.hosts import (
    HOST_ADDRESS_KEY,
    HOST_NAME_KEY,
    HOST_SERVICE_NAME_KEY,
    HOST_SERVICE_USER_KEY,
    HostLeaf,
)

if ty.TYPE_CHECKING:
    from gettext import gettext as _


class SSHLeaf(HostLeaf):
    """The SSH host. Using name defined in `Host` or by `Match` statement.
    If `Hostname` is not defined in ssh config - is set to  `name`.
    """

    def __init__(
        self, name: str, hostname: str | None = None, user: str | None = None
    ) -> None:
        slots = {
            HOST_NAME_KEY: name,
            HOST_ADDRESS_KEY: hostname or name,
            HOST_SERVICE_NAME_KEY: "ssh",
        }
        if user:
            slots[HOST_SERVICE_USER_KEY] = user

        HostLeaf.__init__(self, slots, name)

    def get_description(self) -> str:
        host = str(self[HOST_ADDRESS_KEY])
        with suppress(KeyError):
            if user := self[HOST_SERVICE_USER_KEY]:
                host = f"{user}@{host}"

        return _("SSH host: %s") % host

    def get_gicon(self):
        return icons.ComposedIconSmall(self.get_icon_name(), "terminal")

    def get_text_representation(self) -> str:
        host = str(self[HOST_ADDRESS_KEY])
        with suppress(KeyError):
            if user := self[HOST_SERVICE_USER_KEY]:
                host = f"{user}@{host}"

        return f"ssh://{host}"

    def get_urilist_representation(self) -> list[str]:
        return [self.get_text_representation()]


class SSHConnect(Action):
    """Used to launch a terminal connecting to the specified SSH host.
    HOST_NAME_KEY is used for making connections.
    """

    def __init__(self):
        Action.__init__(self, name=_("Connect"))
        self.kupfer_add_alias("scp")

    def activate(self, leaf, iobj=None, ctx=None):
        host = leaf[HOST_NAME_KEY]
        with suppress(KeyError):
            if user := leaf[HOST_SERVICE_USER_KEY]:
                host = f"{user}@{host}"

        launch.spawn_in_terminal(["ssh", host])

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


class ScpFile(Action):
    """Send file or directory to remote host via scp."""

    def __init__(self):
        super().__init__(name=_("Send file to..."))

    def activate(self, leaf, iobj=None, ctx=None):
        assert leaf and isinstance(leaf, FileLeaf)
        assert iobj and isinstance(iobj, SSHLeaf)

        host = iobj[HOST_NAME_KEY]
        with suppress(KeyError):
            if user := iobj[HOST_SERVICE_USER_KEY]:
                host = f"{user}@{host}"

        cmd = ["scp"]
        if leaf.is_dir():
            cmd += ["-r"]

        cmd += [leaf.object, f"{host}:"]
        launch.spawn_in_terminal(cmd)

    def valid_for_item(self, leaf):
        return os.access(leaf.object, os.R_OK)

    def requires_object(self):
        return True

    def item_types(self):
        yield FileLeaf

    def object_types(self):
        yield SSHLeaf

    def get_description(self):
        return _("Copy file or directory to remote host using scp")

    def get_icon_name(self):
        return "go-next"


def _parse_host_stms(args: list[str]) -> ty.Iterator[tuple[str, str | None]]:
    """Load names from `Host` statement. Ignore names with `*` and exclusions."""
    for host in args:
        if "*" in host or host[0] == "!":
            continue

        user, _, host = host.partition("@")  # noqa:PLW2901
        if user and host:
            yield host, user
        else:
            yield user, None


def _parse_match_stmt(args: list[str]) -> tuple[str, str | None] | None:
    """Parse `Match` arguments and return tuple of (host, optional user)
    or None.

    Load only `User` and `Host` keys from this statement.
    """
    user = None
    host = None
    for key, val in itertools.pairwise(args):
        if "*" in val or val[0] == "!":
            continue

        key = key.lower()  # noqa:PLW2901
        if key == "host":
            host = val
        elif key == "user":
            user = val

    if not host:
        return None

    return host, user


class SSHSource(ToplevelGroupingSource, FilesystemWatchMixin):
    """Reads ~/.ssh/config and creates leaves for the hosts found."""

    source_scan_interval: int = 3600

    _ssh_home = os.path.expanduser("~/.ssh")
    _config_path = os.path.join(_ssh_home, "config")

    def __init__(self, name=_("SSH Hosts")):
        ToplevelGroupingSource.__init__(self, name, "hosts")
        self._version = 2
        self.monitor_token = None

    def initialize(self):
        ToplevelGroupingSource.initialize(self)
        self.monitor_token = self.monitor_files(self._config_path)

    def monitor_include_file(self, gfile):
        return gfile.get_path() in (self._config_path, self._ssh_home)

    def _get_items(self) -> ty.Iterable[SSHLeaf]:
        with open(self._config_path, encoding="UTF-8") as cfile:
            current_hosts: list[tuple[str, str | None]] = []
            current_hostname: str | None = None
            for line in cfile:
                line = line.strip()  # noqa:PLW2901
                if not line:
                    continue

                head, *args = line.split()
                head = head.lower()
                if head in ("host", "match"):
                    # new restriction, flush current data
                    for host, user in current_hosts:
                        yield SSHLeaf(host, current_hostname, user)

                    current_hosts.clear()
                    current_hostname = None

                    if head == "host":
                        # process only 'host' restriction; skip wildcard and
                        # negative entries
                        current_hosts = list(_parse_host_stms(args))
                    elif len(args) > 1 and (
                        hostuser := _parse_match_stmt(args)
                    ):
                        # process "key val" parameters of match
                        current_hosts = [hostuser]

                elif head == "hostname" and args:
                    # if found hostname use is as HOST_ADDRESS_KEY
                    current_hostname = args[0]

            for host, user in current_hosts:
                yield SSHLeaf(host, current_hostname, user)

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
        return "network-workgroup"

    def provides(self):
        yield SSHLeaf
