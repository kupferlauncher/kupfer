# -*- coding: UTF-8 -*-
'''
virtualbox_ose_support.py

Control VirtualBox via command-line interface.
Support both Sun VirtualBox and VirtualBox OpenSource Edition.
'''
from __future__ import with_statement

__revision__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
from xml.dom import minidom
from kupfer import pretty, utils
import virtualbox_const

_VBOX_CONFIG_DIR = os.path.expanduser('~/.VirtualBox/')
_VBOX_CONFIG_FILE = os.path.join(_VBOX_CONFIG_DIR, 'VirtualBox.xml')

MONITORED_DIRS = (_VBOX_CONFIG_DIR, )
IS_DYNAMIC = False
ICON = "virtualbox-ose"

# parameters for VBoxManage
_ACTIONS = {
		virtualbox_const.VM_POWEROFF: 'poweroff',
		virtualbox_const.VM_ACPI_POWEROFF: 'acpipowerbutton',
		virtualbox_const.VM_PAUSE: 'pause',
		virtualbox_const.VM_REBOOT: 'reset',
		virtualbox_const.VM_RESUME: 'resume',
		virtualbox_const.VM_SAVE: 'savestate'
}


def get_machine_state(vm_uuid):
	''' check vms state (on/off/paused) '''
	state = virtualbox_const.VM_STATE_POWEROFF
	try:
		str_state = 'poweroff'
		with os.popen('VBoxManage showvminfo %s --machinereadable' % vm_uuid) \
				as pinfo:
			for line in pinfo:
				if line.startswith('VMState="'):
					str_state = line.strip()[9:-1]
					break
		if str_state == 'paused':
			state = virtualbox_const.VM_STATE_PAUSED
		elif str_state == 'running':
			state = virtualbox_const.VM_STATE_POWERON

	except IOError, err:
		pretty.print_error(__name__, 'get_machine_state', vm_uuid, 'error', err)
		state = virtualbox_const.VM_STATE_POWEROFF

	return state


def vm_action(action, vm_uuid):
	''' change state of the virtual machine. Call VBoxManage.
		@param action - one of the const VM_*
		@param vm_uuid - virtual machine uuid
	'''
	if action == virtualbox_const.VM_START_NORMAL:
		utils.launch_commandline('VBoxManage startvm ' + vm_uuid + \
				' --type gui')
	elif action == virtualbox_const.VM_START_HEADLESS:
		utils.launch_commandline('VBoxManage startvm ' + vm_uuid + \
				' --type headless')
	else:
		command = _ACTIONS[action]
		utils.launch_commandline('VBoxManage controlvm ' + vm_uuid + ' ' + \
				command)


def _get_virtual_machines(config_file):
	''' load (virtual machine uuid, path to vm config) from virtualbox 
		configuration.
		@param config_file - path to VirtualBox.xml file
	'''
	try:
		dtree = minidom.parse(config_file)
		machine_registry = dtree.getElementsByTagName('MachineRegistry')[0]
		for machine in machine_registry.getElementsByTagName('MachineEntry'):
			yield (machine.getAttribute('uuid')[1:-1], machine.getAttribute('src'))

	except StandardError, err:
		pretty.print_error(__name__, '_get_virtual_machines', config_file, 
				'error', err)


def _get_machine_info(vm_uuid, config_file):
	''' load information about virtual machines from its configuration file.
		@param vm_uuid - uuid virtual machine
		@param config_file - path to vm configuration file
	'''
	if not os.path.isfile(config_file):
		return None, None

	try:
		dtree = minidom.parse(config_file)
		machine_registry = dtree.getElementsByTagName('Machine')[0]

		os_type = machine_registry.getAttribute('OSType')
		name = machine_registry.getAttribute('name')

		description = None
		for machine_registry_child in machine_registry.childNodes:
			if machine_registry_child.nodeName == 'Description':
				if machine_registry_child.hasChildNodes():
					description = machine_registry_child.firstChild.nodeValue
				break

		return (name, description or os_type)

	except StandardError, err:
		pretty.print_error(__name__, '_get_machine_info', vm_uuid, 'error' + \
				config_file, err)

	return None, None


def get_machines():
	if os.path.isfile(_VBOX_CONFIG_FILE):
		for vm_uuid, config in _get_virtual_machines(_VBOX_CONFIG_FILE):
			name, description = _get_machine_info(vm_uuid, config)
			if name:
				yield (vm_uuid, name, description)



