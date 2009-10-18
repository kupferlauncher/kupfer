# -*- coding: UTF-8 -*-
'''
virtualbox_vboxapi_support.py

Control VirtualBox via Python interface (vboxapi).
Only (?) Sun VirtualBox (no OSE).
'''
__revision__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

from kupfer import pretty 

#raise ImportError()

import vboxapi

import virtualbox_const

MONITORED_DIRS = None
IS_DYNAMIC = False
ICON = "VBox"


_ACTIONS = {
		virtualbox_const.VM_POWEROFF:		lambda c:c.powerDown(),
		virtualbox_const.VM_ACPI_POWEROFF:	lambda c:c.powerButton(),
		virtualbox_const.VM_PAUSE:			lambda c:c.pause(),
		virtualbox_const.VM_REBOOT:			lambda c:c.reset(),
		virtualbox_const.VM_RESUME:			lambda c:c.resume(),
		virtualbox_const.VM_SAVE:			lambda c:c.saveState()
}


def _get_object_session():
	''' get new session to vm '''
	vbox, session = None, None
	try:
		vbox = vboxapi.VirtualBoxManager(None, None)
		session = vbox.mgr.getSessionObject(vbox.vbox)
	except Exception, err:
		pretty.print_error(__name__, 'virtualbox: get session error ', err)

	return vbox, session

def _get_existing_session(vm_uuid):
	''' get existing session by machine uuid '''
	vbox, session = None, None
	try:
		vbox = vboxapi.VirtualBoxManager(None, None)
		session = vbox.mgr.getSessionObject(vbox.vbox)
		vbox.vbox.openExistingSession(session, vm_uuid)
	except Exception, err:
		pretty.print_error(__name__, 'virtualbox: get session to %s error' % \
				vm_uuid, err)

	return vbox, session

def get_machine_state(machine_id):
	''' check vms state (on/off/paused) '''
	
	vbox, vbox_sess = _get_object_session()
	if vbox_sess is None:
		return virtualbox_const.VM_STATE_POWEROFF

	state = virtualbox_const.VM_STATE_POWERON
	try:
		vbox.vbox.openExistingSession(vbox_sess, machine_id)
		machine_state = vbox_sess.machine.state
		if machine_state == vbox.constants.MachineState_Paused:
			state = virtualbox_const.VM_STATE_PAUSED
		elif machine_state in (vbox.constants.MachineState_PoweredOff, 
				vbox.constants.MachineState_Aborted,
				vbox.constants.MachineState_Starting):
			state = virtualbox_const.VM_STATE_POWEROFF
	except Exception: # exception == machine is off (xpcom.Exception)
		# silently set state to off
		state = virtualbox_const.VM_STATE_POWEROFF

	if vbox_sess.state == vbox.constants.SessionState_Open:
		vbox_sess.close()

	return state


def _machine_start(vm_uuid, mode):
	''' Start virtual machine 
		@param vm_uuid - uuid of virtual machine
		@param mode - mode: gui, headless
	'''
	vbox, session = _get_object_session()
	if session:
		try:
			remote_sess = vbox.vbox.openRemoteSession(session, vm_uuid, mode, '')
			remote_sess.waitForCompletion(-1)
		except Exception, err: 
			pretty.print_error(__name__, "StartVM:", vm_uuid, "Mode ", mode, 
					"error", err)

		if session.state == vbox.constants.SessionState_Open:
			session.close()


def _execute_machine_action(vm_uuid, action):
	''' Start virtual machine 
		@param vm_uuid - uuid of virtual machine
		@param action - function called on vbox session
	'''
	vbox, session = _get_existing_session(vm_uuid)
	try:
		action(session.console)
	except Exception, err: 
		pretty.print_error(__name__, "_execute_machine_action:", repr(action),
				" vm:", vm_uuid, "error", err)

	if session.state == vbox.constants.SessionState_Open:
		session.close()


def vm_action(action, vm_uuid):
	''' change state of the virtual machine 
		@param action - one of the const VM_*
		@param vm_uuid - virtual machine uuid
	'''
	if action == virtualbox_const.VM_START_NORMAL:
		_machine_start(vm_uuid, 'gui')
	elif action == virtualbox_const.VM_START_HEADLESS:
		_machine_start(vm_uuid, 'headless')
	else:
		command = _ACTIONS[action]
		_execute_machine_action(vm_uuid, command)


def get_machines():
	''' Get generator of items: (machine uuid, machine name, machine description)
	'''
	vbox, vbox_sess = _get_object_session()
	if vbox_sess is None:
		return

	machines = vbox.getArray(vbox.vbox, 'machines')
	for machine in machines:
		description = machine.description or machine.OSTypeId
		yield (machine.id, machine.name, description)



