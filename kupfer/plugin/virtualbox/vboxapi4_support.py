"""
virtualbox_vboxapi_support.py

Control VirtualBox via Python interface (vboxapi).
Only (?) Sun VirtualBox (no OSE).
"""
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__version__ = "2018-10-21"

import vboxapi

from kupfer.support import pretty
from kupfer.plugin.virtualbox import constants as vbox_const

# check api
try:
    vboxapi.VirtualBoxReflectionInfo(None).SessionState_Locked
except AttributeError:
    raise ImportError()


MONITORED_DIRS = None
IS_DYNAMIC = False
ICON = "VBox"
APP_ID = "virtualbox"


_ACTIONS = {
    vbox_const.VM_POWEROFF: lambda c: c.powerDown(),
    vbox_const.VM_ACPI_POWEROFF: lambda c: c.powerButton(),
    vbox_const.VM_PAUSE: lambda c: c.pause(),
    vbox_const.VM_REBOOT: lambda c: c.reset(),
    vbox_const.VM_RESUME: lambda c: c.resume(),
    vbox_const.VM_SAVE: lambda c: c.saveState(),
}


_VBOX = vboxapi.VirtualBoxManager(None, None)


def get_machine_by_id(mid):
    try:
        mach = _VBOX.getVirtualBox().getMachine(mid)
    except AttributeError:
        mach = _VBOX.getVirtualBox().findMachine(mid)

    return mach


def get_machine_state(machine_id):
    """check vms state (on/off/paused)"""
    if _VBOX is None:
        return vbox_const.VM_STATE_POWEROFF

    state = vbox_const.VM_STATE_POWERON
    machine_state = None
    try:
        machine = get_machine_by_id(machine_id)
        pretty.print_debug(__name__, "machine ", repr(machine))
        machine_state = machine.state
        if machine_state == _VBOX.constants.MachineState_Paused:
            state = vbox_const.VM_STATE_PAUSED
        elif machine_state in (
            _VBOX.constants.MachineState_PoweredOff,
            _VBOX.constants.MachineState_Aborted,
            _VBOX.constants.MachineState_Starting,
        ):
            state = vbox_const.VM_STATE_POWEROFF
        elif machine_state == _VBOX.constants.MachineState_Saved:
            state = vbox_const.VM_STATE_SAVED

    except Exception as err:  # exception == machine is off (xpcom.Exception)
        pretty.print_debug(__name__, "get_machine_state", machine_state, err)
        # silently set state to off
        state = vbox_const.VM_STATE_POWEROFF

    return state


def _machine_start(vm_uuid, mode):
    """Start virtual machine
    @param vm_uuid - uuid of virtual machine
    @param mode - mode: gui, headless
    """
    try:
        session = _VBOX.getSessionObject()
        mach = get_machine_by_id(vm_uuid)
        remote_sess = mach.launchVMProcess(session, mode, "")
        remote_sess.waitForCompletion(-1)
        session.unlockMachine()
    except Exception as err:
        pretty.print_error(
            __name__, "StartVM:", vm_uuid, "Mode ", mode, "error", err
        )


def _execute_machine_action(vm_uuid, action):
    """Start virtual machine
    @param vm_uuid - uuid of virtual machine
    @param action - function called on _VBOX session
    """
    try:
        session = _VBOX.getSessionObject()
        mach = get_machine_by_id(vm_uuid)
        mach.lockMachine(session, _VBOX.constants.LockType_Shared)
        action(session.console)
        session.unlockMachine()
    except Exception as err:
        pretty.print_error(
            __name__,
            "_execute_machine_action:",
            repr(action),
            " vm:",
            vm_uuid,
            "error",
            err,
        )


def vm_action(action, vm_uuid):
    """change state of the virtual machine
    @param action - one of the const VM_*
    @param vm_uuid - virtual machine uuid
    """
    if _VBOX is None:
        return

    if action == vbox_const.VM_START_NORMAL:
        _machine_start(vm_uuid, "gui")
    elif action == vbox_const.VM_START_HEADLESS:
        _machine_start(vm_uuid, "headless")
    else:
        command = _ACTIONS[action]
        _execute_machine_action(vm_uuid, command)


def get_machines():
    """Get generator of items:
    (machine uuid, machine name, machine description)
    """
    if _VBOX is None:
        return

    machines = _VBOX.getArray(_VBOX.getVirtualBox(), "machines")
    for machine in machines:
        if machine.accessible:
            description = machine.description or machine.OSTypeId
            yield (machine.id, machine.name, description)


def unload():
    pass
