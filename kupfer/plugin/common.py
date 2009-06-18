from kupfer.objects import Leaf, Action, Source
from kupfer import objects, utils
from kupfer.plugin import about

import gtk

class RunnableLeaf (Leaf):
	"""Leaf where the Leaf is basically the action itself,
	for items such as Quit, Log out etc. Is executed by the
	only action Do
	"""
	def __init__(self, obj=None, name=None):
		super(RunnableLeaf, self).__init__(obj, name)
	def get_actions(self):
		yield Do()
	def run(self):
		pass

class Do (Action):
	def __init__(self, name=None):
		if not name: name = _("Do")
		super(Do, self).__init__(name=name)
	def activate(self, leaf):
		leaf.run()
	def get_description(self):
		return _("Perform action")
	def get_icon_name(self):
		return gtk.STOCK_EXECUTE

class Quit (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("Quit")
		super(Quit, self).__init__(name=name)
	def run(self):
		gtk.main_quit()
	def get_description(self):
		return _("Quit Kupfer")
	def get_icon_name(self):
		return gtk.STOCK_QUIT

class Logout (RunnableLeaf):
	"""Log out from desktop"""
	def __init__(self, name=None):
		if not name: name = _("Log out...")
		super(Logout, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-panel-logout", _("Log out..."))
		if not ret:
			utils.launch_commandline("gnome-session-save --kill", _("Log out..."))
	def get_description(self):
		return _("Log out or change user")
	def get_icon_name(self):
		return "system-log-out"

class Shutdown (RunnableLeaf):
	"""Shutdown computer or reboot"""
	def __init__(self, name=None):
		if not name: name = _("Shut down...")
		super(Shutdown, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-panel-logout --shutdown", _("Shut down..."))
		if not ret:
			utils.launch_commandline("gnome-session-save --kill", _("Shut down..."))

	def get_description(self):
		return _("Shut down, restart or suspend computer")
	def get_icon_name(self):
		return "system-shutdown"

class LockScreen (RunnableLeaf):
	"""Lock screen"""
	def __init__(self, name=None):
		if not name: name = _("Lock screen")
		super(LockScreen, self).__init__(name=name)
	def run(self):
		ret = utils.launch_commandline("gnome-screensaver-command --lock", _("Lock screen"))
	def get_description(self):
		return _("Enable screensaver and lock")
	def get_icon_name(self):
		return "system-lock-screen"

class About (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("About Kupfer")
		super(About, self).__init__(name=name)
	def run(self):
		about.show_about_dialog()
	def get_description(self):
		return _("Show information about Kupfer authors and license")
	def get_icon_name(self):
		return gtk.STOCK_ABOUT

class Preferences (RunnableLeaf):
	def __init__(self, name=None):
		if not name: name = _("Kupfer Preferences")
		super(Preferences, self).__init__(name=name)
	def run(self):
		pass
	def get_description(self):
		return _("Settings are not implemented yet; see 'kupfer --help'")
	def get_actions(self):
		return ()
	def get_icon_name(self):
		return gtk.STOCK_PREFERENCES

class Trash (objects.Leaf):
	def __init__(self):
		super(Trash, self).__init__("trash:///", _("Trash"))
	def get_actions(self):
		yield objects.OpenDirectory()
	def get_icon_name(self):
		return "gnome-stock-trash"

class Computer (objects.Leaf):
	def __init__(self):
		super(Computer, self).__init__("computer://", _("Computer"))
	def get_actions(self):
		yield objects.OpenDirectory()
	def get_description(self):
		return _("Browse local disks and mounts")
	def get_icon_name(self):
		return "computer"

class CommonSource (Source):
	def __init__(self, name=_("Special items")):
		super(CommonSource, self).__init__(name)
	def is_dynamic(self):
		return True
	def get_items(self):
		return (
			About(),
			Preferences(),
			Quit(),
			Computer(),
			Trash(),
			Logout(),
			LockScreen(),
			Shutdown(),
		)
	def get_description(self):
		return _("Items and special actions")
	def get_icon_name(self):
		return "gnome-other"
