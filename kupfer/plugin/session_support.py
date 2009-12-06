'''
Common objects for session_* plugins.
'''

from kupfer.objects import Source, RunnableLeaf
from kupfer import utils, pretty

__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


def launch_commandline_with_fallbacks(commands, print_error=True):
	"""Try the sequence of @commands with utils.launch_commandline,
	and return with the first successful command.
	return False if no command is successful and log an error
	"""
	for command in commands:
		ret = utils.launch_commandline(command)
		if ret: return ret
	pretty.print_error(__name__, "Unable to run command(s)", commands)
	return False

class Logout (RunnableLeaf):
	"""Log out from desktop"""
	def __init__(self, commands, name=None):
		if not name: name = _("Log Out...")
		super(Logout, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)
	def get_description(self):
		return _("Log out or change user")
	def get_icon_name(self):
		return "system-log-out"

class Shutdown (RunnableLeaf):
	"""Shutdown computer or reboot"""
	def __init__(self, commands, name=None):
		if not name: name = _("Shut Down...")
		super(Shutdown, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)

	def get_description(self):
		return _("Shut down, restart or suspend computer")
	def get_icon_name(self):
		return "system-shutdown"

class LockScreen (RunnableLeaf):
	"""Lock screen"""
	def __init__(self, commands, name=None):
		if not name: name = _("Lock Screen")
		super(LockScreen, self).__init__(name=name)
		self._commands = commands
	def run(self):
		launch_commandline_with_fallbacks(self._commands)
	def get_description(self):
		return _("Enable screensaver and lock")
	def get_icon_name(self):
		return "system-lock-screen"

class CommonSource (Source):
	def __init__(self, name=_("Special Items")):
		super(CommonSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_description(self):
		return _("Items and special actions")
	def get_icon_name(self):
		return "applications-other"
	def provides(self):
		yield SpecialLocation
		yield RunnableLeaf
