"""
virtualbox_vboxapi_support.py

Control VirtualBox via Python interface (vboxapi).
Only (?) Sun VirtualBox (no OSE).
"""

__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__version__ = "2018-09-07"

from contextlib import suppress

import vboxapi  # pylint: disable=import-error

from kupfer.plugin.virtualbox import constants as vbox_const
from kupfer.support import pretty

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


def _get_object_session():
    """get new session to vm"""
    pretty.print_debug(__name__, "_get_object_session start")
    vbox, session = None, None
    try:
        vbox = vboxapi.VirtualBoxManager(None, None)
        session = vbox.mgr.getSessionObject(vbox.vbox)
    except Exception as err:
        pretty.print_error(__name__, "virtualbox: get session error ", err)

    pretty.print_debug(__name__, "_get_object_session finished", vbox, session)
    return vbox, session


def _get_existing_session(vm_uuid):
    """get existing session by machine uuid"""
    pretty.print_debug(__name__, "_get_existing_session start")
    vbox, session = None, None
    try:
        vbox = vboxapi.VirtualBoxManager(None, None)
        session = vbox.mgr.getSessionObject(vbox.vbox)
        vbox.vbox.openExistingSession(session, vm_uuid)
    except Exception as err:
        pretty.print_error(
            __name__, "virtualbox: get session error", vm_uuid, err
        )

    pretty.print_debug(
        __name__, "_get_existing_session finished", vbox, session
    )
    return vbox, session


def get_machine_state(machine_id):
    """check vms state (on/off/paused)"""
    pretty.print_debug(__name__, "get_machine_state", machine_id)
    vbox, vbox_sess = _get_object_session()
    if vbox_sess is None:
        return vbox_const.VM_STATE_POWEROFF

    state = vbox_const.VM_STATE_POWERON
    try:
        vbox.vbox.openExistingSession(vbox_sess, machine_id)
        machine_state = vbox_sess.machine.state
        if machine_state == vbox.constants.MachineState_Paused:
            state = vbox_const.VM_STATE_PAUSED
        elif machine_state in (
            vbox.constants.MachineState_PoweredOff,
            vbox.constants.MachineState_Aborted,
            vbox.constants.MachineState_Starting,
        ):
            state = vbox_const.VM_STATE_POWEROFF
        elif machine_state == vbox.constants.MachineState_Saved:
            state = vbox_const.VM_STATE_SAVED

    except Exception as err:  # exception == machine is off (xpcom.Exception)
        # silently set state to off
        state = vbox_const.VM_STATE_POWEROFF
        pretty.print_debug(__name__, "get_machine_state error", err)

    with suppress(Exception):
        if vbox_sess.state == vbox.constants.SessionState_Open:
            vbox_sess.close()

    pretty.print_debug(__name__, "get_machine_state finish", machine_id, state)
    return state


def _machine_start(vm_uuid, mode):
    """Start virtual machine
    @param vm_uuid - uuid of virtual machine
    @param mode - mode: gui, headless
    """
    vbox, session = _get_object_session()
    if session:
        try:
            remote_sess = vbox.vbox.openRemoteSession(
                session, vm_uuid, mode, ""
            )
            remote_sess.waitForCompletion(-1)
        except Exception as err:
            pretty.print_error(
                __name__, "StartVM:", vm_uuid, "Mode ", mode, "error", err
            )

        with suppress(Exception):  # various errors (xpcom.Exception)
            if session.state == vbox.constants.SessionState_Open:
                session.close()


def _execute_machine_action(vm_uuid, action):
    """Start virtual machine
    @param vm_uuid - uuid of virtual machine
    @param action - function called on vbox session
    """
    vbox, session = _get_existing_session(vm_uuid)
    try:
        action(session.console)
    except Exception as err:
        pretty.print_error(
            __name__,
            "_execute_machine_action:",
            action,
            " vm:",
            vm_uuid,
            "error",
            err,
        )

    with suppress(Exception):  # various errors (xpcom.Exception)
        if session.state == vbox.constants.SessionState_Open:
            session.close()


def vm_action(action, vm_uuid):
    """change state of the virtual machine
    @param action - one of the const VM_*
    @param vm_uuid - virtual machine uuid
    """
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
    pretty.print_debug(__name__, "get_machines start")
    vbox, vbox_sess = _get_object_session()
    if vbox_sess is None:
        return

    machines = vbox.getArray(vbox.vbox, "machines")
    for machine in machines:
        pretty.print_debug(
            __name__, "get_machines; found machine", machine.id, machine.name
        )
        description = machine.description or machine.OSTypeId
        yield (machine.id, machine.name, description)

    pretty.print_debug(__name__, "get_machines finished")


def unload():
    pass
