# -*- coding: UTF-8 -*-
__kupfer_name__ = _("SSH Hosts")
__description__ = _("Adds the SSH hosts found in ~/.ssh/config.")
__version__ = "2010-04-11"
__author__ = "Fabian Carlström"

__kupfer_sources__ = ("SSHSource", )

import codecs
import os

from kupfer import icons, utils, plugin_support
from kupfer.objects import Leaf, Action, Source
from kupfer.obj.helplib import FilesystemWatchMixin

__kupfer_settings__  = plugin_support.PluginSettings(
	{
		"key": "terminal_emulator",
		"label": _("Preferred terminal"),
		"type": str,
		"value": "terminal",
		"alternatives": ("terminal", "gnome-terminal", "konsole", "urxvt",
		                 "urxvtc"),
		"tooltip": _("The preferred terminal emulator. It's used to "
		              "launch the SSH sessions.")
	},
	{
		"key": "terminal_emulator_exarg",
		"label": _("Execute flag"),
		"type": str,
		"value": "-x",
		"alternatives": ("-x", "-e"),
		"tooltip": _("The flag which makes the terminal execute "
		             "everything following it inside the terminal "
		             "(e.g. '-x' for gnome-terminal and terminal, "
		             "'-e' for konsole and urxvt).")
	},
	#plugin_support.SETTING_PREFER_CATALOG
)


class SSHLeaf (Leaf):
	"""The SSH host. It only stores the "Host" as it was
	specified in the ssh config.
	"""
	def __init__(self, name):
		Leaf.__init__(self, obj=name, name=_(name))

	def get_actions(self):
		yield SSHConnect()

	def get_description(self):
		return _("SSH host")

	def get_icon_name(self):
		return "applications-internet"

class SSHConnect (Action):
	"""Used to launch a terminal connecting to the specified
	SSH host.
	"""
	def __init__(self):
		Action.__init__(self, name=_("Connect to"))

	def activate(self, leaf):
		terminal = __kupfer_settings__["terminal_emulator"]
		exarg = __kupfer_settings__["terminal_emulator_exarg"]
		utils.spawn_async([terminal, exarg, "ssh", leaf.object])

	def get_description(self):
		return _("Connect to SSH host")

	def get_icon_name(self):
		return "network-server"


class SSHSource (Source, FilesystemWatchMixin):
	"""Reads ~/.ssh/config and creates leaves for the hosts found.
	"""
	_ssh_home = os.path.expanduser("~/.ssh/")
	_ssh_config_file = "config"
	_config_path = os.path.join(_ssh_home, _ssh_config_file)

	def __init__(self, name=_("SSH Hosts")):
		Source.__init__(self, name)

	def initialize(self):
		self.monitor_token = self.monitor_directories(self._ssh_home)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() == self._ssh_config_file

	def get_items(self):
		try:
			content = codecs.open(self._config_path, "r", "UTF-8").readlines()
			for line in content:
				line = line.strip()
				words = line.split()
				# Take every word after "Host" as an individual host
				# we must skip entries with wildcards
				if words and words[0].lower() == "host":
					for word in words[1:]:
						if "*" in word:
							continue
						yield SSHLeaf(word)
		except EnvironmentError, exc:
			self.output_error(exc)
		except UnicodeError, exc:
			self.output_error("File %s not in expected encoding (UTF-8)" %
					self._config_path)
			self.output_error(exc)

	def get_description(self):
		return _("SSH hosts as specified in ~/.ssh/config")

	def get_icon_name(self):
		return "applications-internet"

	def provides(self):
		yield SSHLeaf

