# -*- coding: UTF-8 -*-

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.helplib import PicklingHelperMixin, FilesystemWatchMixin
from kupfer import pretty, plugin_support

__kupfer_name__ = _("VirtualBox")
__kupfer_sources__ = ("VBoxMachinesSource", )
__description__ = _("Control Sun VirtualBox Virtual Machines")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
__kupfer_settings__ = plugin_support.PluginSettings(
		plugin_support.SETTING_PREFER_CATALOG,
)


try:
	import virtualbox_vboxapi_support as virtualbox_support
	pretty.print_info(__name__, 'Using vboxapi...')
except ImportError, err:
	import virtualbox_ose_support as virtualbox_support
	pretty.print_info(__name__, 'Using cli...', err)


class VirtualMachine(Leaf):
	def __init__(self, obj, name, description):
		Leaf.__init__(self, obj, name)
		self.description = description

	def get_description(self):
		return self.description

	def get_icon_name(self):
		return virtualbox_support.ICON

	def get_actions(self):
		state = virtualbox_support.get_machine_state(self.object)
		if state == virtualbox_support.VM_POWEROFF:
			yield StartVM(_('Power On'), 'system-run', 'gui')
			yield StartVM(_('Power On Headless'), 'system-run', 'headless', -5)
		elif state == virtualbox_support.VM_POWERON:
			yield StdVmAction(_('Send Power Off Signal'), 'system-shutdown', \
					virtualbox_support.machine_acpipoweroff, -5)
			yield StdVmAction(_('Pause'), 'pause', virtualbox_support.machine_pause)
			yield StdVmAction(_('Reboot'), 'system-reboot', virtualbox_support.machine_reboot, -10)
		else: # VM_PAUSED
			yield StdVmAction(_('Resume'), 'resume', virtualbox_support.machine_resume)

		if state in (virtualbox_support.VM_POWERON, virtualbox_support.VM_PAUSED):
			yield StdVmAction(_('Save State'), 'system-supsend', virtualbox_support.machine_save)
			yield StdVmAction(_('Power Off'), 'system-shutdown', virtualbox_support.machine_poweroff, -10)


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
		virtualbox_support.machine_start(leaf.object, self.mode)


class StdVmAction(_VMAction):
	def __init__(self, name, icon, command, rank_adjust=0):
		_VMAction.__init__(self, name, icon)
		self.rank_adjust = rank_adjust
		self.command = command

	def activate(self, leaf):
		self.command(leaf.object)


class VBoxMachinesSource(AppLeafContentMixin, Source, PicklingHelperMixin, FilesystemWatchMixin):
	appleaf_content_id = ('VirtualBox OSE', 'Sun VirtualBox')

	def __init__(self, name=_("Sun VirtualBox Machines")):
		Source.__init__(self, name)
		self.unpickle_finish()

	def unpickle_finish(self):
		if virtualbox_support.MONITORED_DIRS:
			self.monitor_token = self.monitor_directories(*virtualbox_support.MONITORED_DIRS)

	def is_dynamic(self):
		return virtualbox_support.IS_DYNAMIC

	def get_items(self):
		for machine_id, machine_name, machine_desc in virtualbox_support.get_machines():
			yield VirtualMachine(machine_id, machine_name, machine_desc)

	def get_description(self):
		return None

	def get_icon_name(self):
		return virtualbox_support.ICON

	def provides(self):
		yield VirtualMachine



