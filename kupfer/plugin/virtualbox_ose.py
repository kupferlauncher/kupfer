# -*- coding: UTF-8 -*-
from __future__ import with_statement

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin 
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import pretty, plugin_support, utils

__kupfer_name__ = _("VirtualBoxOSE")
__kupfer_sources__ = ("VBoxOseMachinesSource", )
__description__ = _("Control VirtualBox Virtual Machines. This version supports OpenSource Edition.")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)

''' 
This version supports VirtualBox OpenSource Edition, without vboxapi.
Uses coommand-line interface to controll virtual machines, and xml-config files to get list of machines.
Plugin support also Sun (non-ose) VirtualBox.
'''


import os
from xml.dom import minidom


VM_POWEROFF = 0
VM_POWERON = 1
VM_PAUSED = 2


def _get_virtual_machines(config_file):
	try:
		dtree = minidom.parse(config_file)
		machine_registry = dtree.getElementsByTagName('MachineRegistry')[0]
		for machine in machine_registry.getElementsByTagName('MachineEntry'):
			yield (machine.getAttribute('uuid')[1:-1], machine.getAttribute('src'))

	except StandardError, err:
		pretty.output_error(__name__, '_get_virtual_machines error', err)


def _get_machine_info(uuid, config_file):
	if not os.path.isfile(config_file):
		return None, Noen

	try:
		dtree = minidom.parse(config_file)
		machine_registry = dtree.getElementsByTagName('Machine')[0]
		os_type = machine_registry.getAttribute('OSType')
		name = machine_registry.getAttribute('name')
		return (name, os_type)

	except StandardError, err:
		pretty.output_error(__name__, '_get_machine_info error ' + uuid + ' ' + config_file, err)

	return None, None


def _check_machine_state(machine_id):
	''' check vms state (on/off/paused) '''
	state = VM_POWEROFF
	try:
		str_state = 'poweroff'
		with os.popen('VBoxManage showvminfo %s --machinereadable' % machine_id) as pinfo:
			for line in pinfo:
				if line.startswith('VMState="'):
					str_state = line.strip()[9:-1]
					break
		if str_state == 'paused':
			state = VM_PAUSED
		elif str_state == 'poweron':
			state = VM_POWERON
	except IOError, err:
		pretty.output_error(__name__, '_check_machine_state error ' + machine_id, err)
		state = VM_POWEROFF

	return state


class VirtualMachine(Leaf):
	def __init__(self, obj, name, description):
		Leaf.__init__(self, obj, name)
		self.description = description

	def get_description(self):
		return self.description

	def get_icon_name(self):
		return "VBox"

	def get_actions(self):
		# actions depend on machine state
		state = _check_machine_state(self.object)
		if state == VM_POWEROFF:
			yield StartVM(_('Power On'), 'system-run', 'gui')
			yield StartVM(_('Power On Headless'), 'system-run', 'headless', -5)
		elif state == VM_POWERON:
			yield StdVmAction(_('Send Power Off Signal'), 'system-shutdown', \
					'acpipowerbutton', -5)
			yield StdVmAction(_('Pause'), 'pause', 'pause')
			yield StdVmAction(_('Reboot'), 'system-reboot', 'reset', -10)
		else: # VM_PAUSED
			yield StdVmAction(_('Resume'), 'resume', 'resume')

		if state in (VM_POWERON, VM_PAUSED):
			yield StdVmAction(_('Save State'), 'system-supsend', 'savestate')
			yield StdVmAction(_('Power Off'), 'system-shutdown', 'poweroff', -10)


class _VMAction(Action):
	def __init__(self, name, icon):
		Action.__init__(self, name)
		self._icon = icon

	def get_icon_name(self):
		return self._icon

	def item_types(self):
		yield VirtualMachine


class StartVM(_VMAction):
	def __init__(self, name, icon, mode, rank_adjust=0):
		_VMAction.__init__(self, name, icon)
		self.mode = mode
		self.rank_adjust = rank_adjust

	def activate(self, leaf):
		utils.launch_commandline('VBoxManage startvm ' + leaf.object + ' --type ' + self.mode)


class StdVmAction(_VMAction):
	def __init__(self, name, icon, command, rank_adjust=0):
		_VMAction.__init__(self, name, icon)
		self.rank_adjust = rank_adjust
		self.command = command

	def activate(self, leaf):
		utils.launch_commandline('VBoxManage controlvm ' + leaf.object + ' ' + self.command)


class VBoxOseMachinesSource(AppLeafContentMixin, Source, PicklingHelperMixin, FilesystemWatchMixin):
	appleaf_content_id = ('VirtualBox OSE', 'Sun VirtualBox')

	def __init__(self, name=_("VirtualBox Machines")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		self._vbox_config_dir = os.path.expanduser('~/.VirtualBox/')
		self._vbox_config_file = os.path.join(self._vbox_config_dir, 'VirtualBox.xml')
		self.monitor_token = self.monitor_directories(self._vbox_config_dir)

	def is_dynamic(self):
		return False

	def get_items(self):
		if os.path.isfile(self._vbox_config_file):
			for uuid, config in _get_virtual_machines(self._vbox_config_file):
				name, description = _get_machine_info(uuid, config)
				if name:
					yield VirtualMachine(uuid, name, description)

	def get_description(self):
		return None

	def get_icon_name(self):
		return "virtualbox-ose"

	def provides(self):
		yield VirtualMachine



