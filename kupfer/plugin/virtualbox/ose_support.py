"""
virtualbox_ose_support.py

Control VirtualBox via command-line interface.
Support both Sun VirtualBox and VirtualBox OpenSource Edition.
"""

__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__version__ = "2018-10-21"

import os
from pathlib import Path
from xml.dom import minidom

from kupfer import launch
from kupfer.plugin.virtualbox import constants as vbox_const
from kupfer.support import pretty

_VBOX_CONFIG_DIRS = (
    Path("~/.config/VirtualBox/").expanduser(),
    Path("~/.VirtualBox/").expanduser(),
)
_VBOX_CONFIG_FILE = "VirtualBox.xml"

MONITORED_DIRS = _VBOX_CONFIG_DIRS
IS_DYNAMIC = False
ICON = "virtualbox-ose"
APP_ID = "virtualbox-ose"

# parameters for VBoxManage
_ACTIONS = {
    vbox_const.VM_POWEROFF: "poweroff",
    vbox_const.VM_ACPI_POWEROFF: "acpipowerbutton",
    vbox_const.VM_PAUSE: "pause",
    vbox_const.VM_REBOOT: "reset",
    vbox_const.VM_RESUME: "resume",
    vbox_const.VM_SAVE: "savestate",
}


def get_machine_state(vm_uuid):
    """check vms state (on/off/paused)"""
    state = vbox_const.VM_STATE_POWEROFF
    try:
        str_state = "poweroff"
        with os.popen(
            f"VBoxManage showvminfo {vm_uuid} --machinereadable"
        ) as pinfo:
            for line in pinfo:
                if line.startswith('VMState="'):
                    str_state = line.strip()[9:-1]
                    break

        if str_state == "paused":
            state = vbox_const.VM_STATE_PAUSED
        elif str_state == "running":
            state = vbox_const.VM_STATE_POWERON
        elif str_state == "saved":
            state = vbox_const.VM_STATE_SAVED

    except OSError as err:
        pretty.print_error(
            __name__, "get_machine_state", vm_uuid, "error", err
        )
        state = vbox_const.VM_STATE_POWEROFF

    return state


def vm_action(action, vm_uuid):
    """change state of the virtual machine. Call VBoxManage.
    @param action - one of the const VM_*
    @param vm_uuid - virtual machine uuid
    """
    if action == vbox_const.VM_START_NORMAL:
        launch.spawn_async(["VBoxManage", "startvm", vm_uuid, "--type", "gui"])
    elif action == vbox_const.VM_START_HEADLESS:
        launch.spawn_async(
            ["VBoxManage", "startvm", vm_uuid, "--type", "headless"]
        )
    else:
        command = _ACTIONS[action]
        launch.spawn_async(["VBoxManage", "controlvm", vm_uuid, command])


def _get_virtual_machines(config_file):
    """load (virtual machine uuid, path to vm config) from virtualbox
    configuration.
    @param config_file - path to VirtualBox.xml file
    """
    try:
        dtree = minidom.parse(config_file)
        machine_registry = dtree.getElementsByTagName("MachineRegistry")[0]
        for machine in machine_registry.getElementsByTagName("MachineEntry"):
            yield (
                machine.getAttribute("uuid")[1:-1],
                machine.getAttribute("src"),
            )

    except Exception as err:
        pretty.print_error(
            __name__, "_get_virtual_machines", config_file, "error", err
        )


def _get_machine_info(vm_uuid, config_file):
    """load information about virtual machines from its configuration file.
    @param vm_uuid - uuid virtual machine
    @param config_file - path to vm configuration file
    """
    if not os.path.isfile(config_file):
        return None, None

    try:
        dtree = minidom.parse(config_file)
        machine_registry = dtree.getElementsByTagName("Machine")[0]
        os_type = machine_registry.getAttribute("OSType")
        name = machine_registry.getAttribute("name")
        description = None
        for machine_registry_child in machine_registry.childNodes:
            if machine_registry_child.nodeName == "Description":
                if machine_registry_child.hasChildNodes() and (
                    fc := machine_registry_child.firstChild):
                        description = fc.nodeValue

                break

        return (name, description or os_type)

    except Exception as err:
        pretty.print_error(
            __name__, "_get_machine_info", vm_uuid, "error" + config_file, err
        )
    return None, None


def get_machines():
    for dirname in _VBOX_CONFIG_DIRS:
        vbox_conf = Path(dirname, _VBOX_CONFIG_FILE)
        if not vbox_conf.is_file():
            continue

        for vm_uuid, config in _get_virtual_machines(vbox_conf):
            if not os.path.isabs(config):
                config = os.path.join(dirname, config)  # noqa: PLW2901

            name, description = _get_machine_info(vm_uuid, config)
            if name:
                yield (vm_uuid, name, description)


def unload():
    pass
