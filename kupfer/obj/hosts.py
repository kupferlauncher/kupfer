"""
Kupfer's Hosts API

Main definition and *constructor* classes.

"""

import typing as ty

from kupfer.obj.grouping import GroupingLeaf, Slots

__author__ = (
    "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>, "
    "Karol Będkowski <karol.bedkowsk+gh@gmail.com>"
)

HOST_NAME_KEY = "HOST_NAME"
HOST_ADDRESS_KEY = "HOST_ADDRESS"
HOST_SERVICE_NAME_KEY = "HOST_SERVICE_NAME"
HOST_SERVICE_PORT_KEY = "HOST_SERVICE_PORT"
HOST_SERVICE_USER_KEY = "HOST_SERVICE_USER"
HOST_SERVICE_PASS_KEY = "HOST_SERVICE_PASS"
HOST_SERVICE_REMOTE_PATH_KEY = "HOST_SERVICE_REMOTE_PATH"


class HostLeaf(GroupingLeaf):
    grouping_slots = (HOST_NAME_KEY, HOST_ADDRESS_KEY)

    def get_icon_name(self) -> str:
        return "computer"


class HostServiceLeaf(HostLeaf):
    """Leaf dedicated for well known services like ftp, ssh, vnc"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        name: str,
        address: str,
        service: str,
        description: str,
        port: ty.Optional[str] = None,
        user: ty.Optional[str] = None,
        password: ty.Optional[str] = None,
        slots: Slots = None,
    ) -> None:
        _slots = {
            HOST_NAME_KEY: name,
            HOST_ADDRESS_KEY: address,
            HOST_SERVICE_NAME_KEY: service,
            HOST_SERVICE_PORT_KEY: port,
            HOST_SERVICE_USER_KEY: user,
            HOST_SERVICE_PASS_KEY: password,
        }
        if slots:
            _slots.update(slots)

        HostLeaf.__init__(self, _slots, name or address)
        self._description = description

    def get_description(self) -> str:
        return self._description
