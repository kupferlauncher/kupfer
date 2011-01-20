# -*- coding: UTF-8 -*-

__kupfer_name__ = _("VirtualBox")
__kupfer_sources__ = ("VBoxMachinesSource", )
__description__ = _("Control VirtualBox Virtual Machines. "
                    "Supports both Sun VirtualBox and Open Source Edition.")
__version__ = "0.3"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

from kupfer.objects import Leaf, Action, Source
from kupfer import pretty
from kupfer import plugin_support
from kupfer.obj.apps import ApplicationSource

try:
	try:
		from kupfer.plugin.virtualbox import vboxapi4_support as vboxapi_support
		pretty.print_info(__name__, 'Using vboxapi4...')
	except ImportError, err:
		from kupfer.plugin.virtualbox import vboxapi_support
		pretty.print_info(__name__, 'Using vboxapi...')
except ImportError, err:
	pretty.print_info(__name__, 'vboxapi not available...', err)
	vboxapi_support = None

from kupfer.plugin.virtualbox import ose_support
from kupfer.plugin.virtualbox import constants as vbox_const


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key": "force_cli",
		"label": _("Force use CLI interface"),
		"type": bool,
		"value": False,
	},
)


class _VBoxSupportProxy:
	def __getattr__(self, attr):
		vbox = ose_support
		if vboxapi_support and not __kupfer_settings__['force_cli']:
			vbox = vboxapi_support
		return getattr(vbox, attr)


vbox_support = _VBoxSupportProxy()


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
		elif state == vbox_const.VM_STATE_SAVED:
			yield VMAction(_('Power On'), 'system-run',
					vbox_const.VM_START_NORMAL)
			yield VMAction(_('Power On Headless'), 'system-run',
					vbox_const.VM_START_HEADLESS, -5)
		else:  # VM_STATE_PAUSED
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


class VBoxMachinesSource(ApplicationSource):
	appleaf_content_id = vbox_support.APP_ID

	def __init__(self, name=_("VirtualBox Machines")):
		Source.__init__(self, name)

	def initialize(self):
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
