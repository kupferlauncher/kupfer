# -*- coding: UTF-8 -*-

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer import pretty, plugin_support

__kupfer_name__ = _("VirtualBox")
__kupfer_sources__ = ("VBoxMachinesSource", )
__description__ = _("Control VirtualBox Virtual Machines. "
                    "Supports both Sun VirtualBox and Open Source Edition.")
__version__ = "0.3"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)

try:
	from kupfer.plugin.virtualbox import vboxapi_support as vbox_support
	pretty.print_info(__name__, 'Using vboxapi...')
except ImportError, err:
	from kupfer.plugin.virtualbox import ose_support as vbox_support
	pretty.print_info(__name__, 'Using cli...', err)

from kupfer.plugin.virtualbox import constants as vbox_const


class VirtualMachine(Leaf):
	def __init__(self, obj, name, description):
		Leaf.__init__(self, obj, name)
		self.description = description

	def get_description(self):
		return self.description

	def get_icon_name(self):
		return vbox_support.ICON

	def get_actions(self):
		state = vbox_support.get_machine_state(self.object)
		if state == vbox_const.VM_STATE_POWEROFF:
			yield VMAction(_('Power On'), 'system-run',
					vbox_const.VM_START_NORMAL)
			yield VMAction(_('Power On Headless'), 'system-run',
					vbox_const.VM_START_HEADLESS, -5)
		elif state == vbox_const.VM_STATE_POWERON:
			yield VMAction(_('Send Power Off Signal'), 'system-shutdown',
					vbox_const.VM_ACPI_POWEROFF, -5)
			yield VMAction(_('Pause'), 'pause', vbox_const.VM_PAUSE)
			yield VMAction(_('Reboot'), 'system-reboot', 
					vbox_const.VM_REBOOT, -10)
		else: # VM_STATE_PAUSED
			yield VMAction(_('Resume'), 'resume', vbox_const.VM_RESUME)

		if state in (vbox_const.VM_STATE_POWERON, vbox_const.VM_STATE_PAUSED):
			yield VMAction(_('Save State'), 'system-supsend',
					vbox_const.VM_SAVE)
			yield VMAction(_('Power Off'), 'system-shutdown',
					vbox_const.VM_POWEROFF, -10)


class VMAction(Action):
	def __init__(self, name, icon, command, rank_adjust=0):
		Action.__init__(self, name)
		self._icon = icon
		self.rank_adjust = rank_adjust
		self.command = command

	def get_icon_name(self):
		return self._icon

	def item_types(self):
		yield VirtualMachine

	def activate(self, leaf):
		vbox_support.vm_action(self.command, leaf.object)


class VBoxMachinesSource(AppLeafContentMixin, Source, PicklingHelperMixin, 
		FilesystemWatchMixin):
	appleaf_content_id = ('VirtualBox OSE', 'Sun VirtualBox')

	def __init__(self, name=_("VirtualBox Machines")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		if vbox_support.MONITORED_DIRS:
			self.monitor_token = self.monitor_directories(
					*vbox_support.MONITORED_DIRS)

	def is_dynamic(self):
		return vbox_support.IS_DYNAMIC

	def get_items(self):
		for machine_id, machine_name, machine_desc in vbox_support.get_machines():
			yield VirtualMachine(machine_id, machine_name, machine_desc)

	def get_description(self):
		return None

	def get_icon_name(self):
		return vbox_support.ICON

	def provides(self):
		yield VirtualMachine



