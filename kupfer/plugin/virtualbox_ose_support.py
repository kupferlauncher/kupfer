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

VM_POWEROFF = 0
VM_POWERON = 1
VM_PAUSED = 2

_VBOX_CONFIG_DIR = os.path.expanduser('~/.VirtualBox/')
_VBOX_CONFIG_FILE = os.path.join(_VBOX_CONFIG_DIR, 'VirtualBox.xml')

MONITORED_DIRS = (_VBOX_CONFIG_DIR, )
IS_DYNAMIC = False
ICON = "virtualbox-ose"


def get_machine_state(vm_uuid):
	''' check vms state (on/off/paused) '''
	state = VM_POWEROFF
	try:
		str_state = 'poweroff'
		with os.popen('VBoxManage showvminfo %s --machinereadable' % vm_uuid) \
				as pinfo:
			for line in pinfo:
				if line.startswith('VMState="'):
					str_state = line.strip()[9:-1]
					break
		if str_state == 'paused':
			state = VM_PAUSED
		elif str_state == 'running':
			state = VM_POWERON

	except IOError, err:
		pretty.print_error(__name__, 'get_machine_state error ' + vm_uuid, err)
		state = VM_POWEROFF

	return state


def machine_start(vm_uuid, mode):
	utils.launch_commandline('VBoxManage startvm ' + vm_uuid + ' --type ' + mode)

def machine_poweroff(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' poweroff')

def machine_acpipoweroff(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' acpipowerbutton')

def machine_pause(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' pause')

def machine_reboot(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' reset')

def machine_resume(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' resume')

def machine_save(vm_uuid):
	utils.launch_commandline('VBoxManage controlvm ' + vm_uuid+ ' savestate')


def _get_virtual_machines(config_file):
	try:
		dtree = minidom.parse(config_file)
		machine_registry = dtree.getElementsByTagName('MachineRegistry')[0]
		for machine in machine_registry.getElementsByTagName('MachineEntry'):
			yield (machine.getAttribute('uuid')[1:-1], machine.getAttribute('src'))

	except StandardError, err:
		pretty.print_error(__name__, '_get_virtual_machines error', err)


def _get_machine_info(vm_uuid, config_file):
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
		pretty.print_error(__name__, '_get_machine_info error ' + vm_uuid + ' ' + \
				config_file, err)

	return None, None


def get_machines():
	if os.path.isfile(_VBOX_CONFIG_FILE):
		for vm_uuid, config in _get_virtual_machines(_VBOX_CONFIG_FILE):
			name, description = _get_machine_info(vm_uuid, config)
			if name:
				yield (vm_uuid, name, description)



