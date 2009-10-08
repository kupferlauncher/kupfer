# -*- coding: UTF-8 -*-

import os
import sys

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.helplib import FilesystemWatchMixin
from kupfer import pretty, plugin_support

__kupfer_name__ = _("VirtualBox")
__kupfer_sources__ = ("VBoxMachinesSource", )
__description__ = _("Control Sun VirtualBox Virtual Machines")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)

import vboxapi

# try to load xpcom from vbox sdk
xpcom_path = vboxapi.VboxSdkDir+'/bindings/xpcom/python/'
xpcom_Exception = Exception
if os.path.isdir(xpcom_path):
	sys.path.append(xpcom_path)
	try:
		import xpcom
	except ImportError:
		pretty.print_error('Cannot import xpcom')
	else:
		xpcom_Exception = xpcom.Exception


VM_POWEROFF = 0
VM_POWERON = 1
VM_PAUSED = 2


def _get_object_session():
	''' get new session to vm '''
	vbox, session = None, None
	if vboxapi is not None:
		try:
			vbox = vboxapi.VirtualBoxManager(None, None)
			session = vbox.mgr.getSessionObject(vbox.vbox)
		except xpcom_Exception, err:
			vbox = None
			pretty.print_error('_get_object_session error ', err)

	return vbox, session

def _get_existing_session(vm_uuid):
	''' get existing session by machine uuid '''
	vbox, session = None, None
	if vboxapi is not None:
		try:
			vbox = vboxapi.VirtualBoxManager(None, None)
			session = vbox.mgr.getSessionObject(vbox.vbox)
			vbox.vbox.openExistingSession(session, vm_uuid)
		except xpcom_Exception, err:
			vbox = None
			pretty.print_error('_get_existing_session error', err)
	return vbox, session

def _check_machine_state(vbox, vbox_sess, machine_id):
	''' check vms state (on/off/paused) '''
	state = VM_POWERON
	try:
		vbox.vbox.openExistingSession(vbox_sess, machine_id)
		machine_state = vbox_sess.machine.state
		if machine_state == vbox.constants.MachineState_Paused:
			state = VM_PAUSED
		elif machine_state in (vbox.constants.MachineState_PoweredOff, vbox.constants.MachineState_Aborted,
				vbox.constants.MachineState_Starting):
			state = VM_POWEROFF
	except xpcom_Exception, err: # exception == machine is off (xpcom.Exception)
		# silently set state to off
		state = VM_POWEROFF

	if vbox_sess.state == vbox.constants.SessionState_Open:
		vbox_sess.close()

	return state


class VirtualMachine(Leaf):
	def __init__(self, obj, name, state, description):
		Leaf.__init__(self, obj, name)
		self.state = state
		self.description = description

	def get_description(self):
		return self.description

	def get_icon_name(self):
		return "VBox"

	def get_actions(self):
		# actions depend on machine state
		if self.state == VM_POWEROFF:
			yield StartVM(_('Power On'), 'system-run', 'gui')
			yield StartVM(_('Power On Headless'), 'system-run', 'headless', -5)
		elif self.state == VM_POWERON:
			yield StdVmAction(_('Send Power Off Signal'), 'system-shutdown', \
					lambda c:c.powerButton(), -5)
			yield StdVmAction(_('Pause'), 'pause', lambda c:c.pause())
			yield StdVmAction(_('Reboot'), 'system-reboot', lambda c:c.reset(), -10)
		else: # VM_PAUSED
			yield StdVmAction(_('Resume'), 'resume', lambda c:c.resume())

		if self.state in (VM_POWERON, VM_PAUSED):
			yield StdVmAction(_('Save State'), 'system-supsend', lambda c:c.saveState())
			yield StdVmAction(_('Power Off'), 'system-shutdown', lambda c:c.powerDown(), -10)

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
		vbox, session = _get_object_session()
		if vbox:
			try:
				remote_sess = vbox.vbox.openRemoteSession(session, leaf.object, self.mode, '')
				remote_sess.waitForCompletion(-1)
			except xpcom_Exception, err: 
				pretty.print_error('StartVM: ' + self.name + " vm: " + leaf.name + " error", err)

			if session.state == vbox.constants.SessionState_Open:
				session.close()


class StdVmAction(_VMAction):
	def __init__(self, name, icon, command, rank_adjust=0):
		_VMAction.__init__(self, name, icon)
		self.rank_adjust = rank_adjust
		self.command = command

	def activate(self, leaf):
		vbox, session = _get_existing_session(leaf.object)
		if session:
			try:
				self.command(session.console)
			except xpcom_Exception, err: 
				pretty.print_error('StdVmAction: ' + self.name + " vm: " + leaf.name + " error", err)
			if session.state == vbox.constants.SessionState_Open:
				session.close()


class VBoxMachinesSource(AppLeafContentMixin, Source):
	appleaf_content_id = 'Sun VirtualBox'

	def __init__(self, name=_("Sun VirtualBox Machines")):
		Source.__init__(self, name)

	def is_dynamic(self):
		return True

	def get_items(self):
		vbox, vbox_sess = _get_object_session()
		if vbox is None:
			return

		machines = vbox.getArray(vbox.vbox, 'machines')
		session = vbox.mgr.getSessionObject(vbox.vbox)
		for machine in machines:
			state = _check_machine_state(vbox, vbox_sess, machine.id)
			description = machine.description or machine.OSTypeId
			yield VirtualMachine(machine.id, machine.name, state, description)

	def get_description(self):
		return None

	def get_icon_name(self):
		return "VBox"

	def provides(self):
		yield VirtualMachine



