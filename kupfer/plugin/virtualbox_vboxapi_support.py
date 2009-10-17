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

VM_POWEROFF = 0
VM_POWERON = 1
VM_PAUSED = 2

MONITORED_DIRS = None
IS_DYNAMIC = False
ICON = "VBox"

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
		pretty.print_error(__name__, 'virtualbox: get session to %s error' %
				vm_uuid, err)

	return vbox, session

def get_machine_state(machine_id):
	''' check vms state (on/off/paused) '''
	
	vbox, vbox_sess = _get_object_session()
	state = VM_POWERON
	try:
		vbox.vbox.openExistingSession(vbox_sess, machine_id)
		machine_state = vbox_sess.machine.state
		if machine_state == vbox.constants.MachineState_Paused:
			state = VM_PAUSED
		elif machine_state in (vbox.constants.MachineState_PoweredOff, 
				vbox.constants.MachineState_Aborted,
				vbox.constants.MachineState_Starting):
			state = VM_POWEROFF
	except Exception: # exception == machine is off (xpcom.Exception)
		# silently set state to off
		state = VM_POWEROFF

	if vbox_sess.state == vbox.constants.SessionState_Open:
		vbox_sess.close()

	return state


def machine_start(machine_uuid, mode):
	vbox, session = _get_object_session()
	if session:
		try:
			remote_sess = vbox.vbox.openRemoteSession(session, machine_uuid, mode, '')
			remote_sess.waitForCompletion(-1)
		except Exception, err: 
			pretty.print_error(__name__, "StartVM:", machine_uuid, "error", err)

		if session.state == vbox.constants.SessionState_Open:
			session.close()


def _execute_machine_action(machine_uuid, action):
	vbox, session = _get_existing_session(machine_uuid)
	try:
		action(session.console)
	except Exception, err: 
		pretty.print_error(__name__, "_execute_machine_action:", repr(action),
				" vm:", machine_uuid, "error", err)

	if session.state == vbox.constants.SessionState_Open:
		session.close()


def machine_poweroff(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.powerDown())

def machine_acpipoweroff(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.powerButton())

def machine_pause(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.pause())

def machine_reboot(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.reset())

def machine_resume(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.resume())

def machine_save(machine_uuid):
	_execute_machine_action(machine_uuid, lambda c:c.saveState())


def get_machines():
	vbox, vbox_sess = _get_object_session()
	if vbox_sess is None:
		return

	machines = vbox.getArray(vbox.vbox, 'machines')
	for machine in machines:
		description = machine.description or machine.OSTypeId
		yield (machine.id, machine.name, description)



