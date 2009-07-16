from kupfer.objects import Leaf, Action, Source
from kupfer import utils

__kupfer_name__ = _("GNU Screen")
__kupfer_sources__ = ("ScreenSessionsSource", )
__description__ = _("Active GNU Screen sessions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


def screen_sessions_infos():
	"""
	Yield tuples of pid, name, time, status
	for running screen sessions
	"""
	from os import popen
	pipe = popen("screen -list")
	output = pipe.read()
	for line in output.splitlines():
		fields = line.split("\t")
		if len(fields) == 4:
			empty, pidname, time, status = fields
			pid, name = pidname.split(".", 1)
			time = time.strip("()")
			status = status.strip("()")
			yield (pid, name, time, status)

class ScreenSession (Leaf):
	"""Represented object is the session pid as string"""
	def get_actions(self):
		return (AttachScreen(),)

	def get_description(self):
		for pid, name, time, status in screen_sessions_infos():
			if self.object == pid:
				break
		else:
			return "%s (%s)" % (self.name, self.object)
		# Handle localization of status
		status_dict = {
			"Attached": _("Attached"),
			"Detached": _("Detached"),
		}
		status = status_dict.get(status, status)
		return (_("%(status)s session %(name)s (%(pid)s) created %(time)s") %
				{"status": status, "name": name, "pid": pid, "time": time})

	def get_icon_name(self):
		return "gnome-window-manager"

class ScreenSessionsSource (Source):
	"""Source for GNU Screen sessions"""
	def __init__(self):
		super(ScreenSessionsSource, self).__init__(_("Screen sessions"))
	def is_dynamic(self):
		return True
	def get_items(self):
		for pid, name, time, status in screen_sessions_infos():
			yield ScreenSession(pid, name)

	def get_description(self):
		return _("Active GNU Screen sessions")
	def get_icon_name(self):
		return "terminal"
	def provides(self):
		yield ScreenSession

class AttachScreen (Action):
	"""
	"""
	def __init__(self):
		name = _("Attach")
		super(AttachScreen, self).__init__(name)
	def activate(self, leaf):
		pid = leaf.object
		action = "screen -x -R %s" % pid
		utils.launch_commandline(action, name=_("GNU Screen session"),
				in_terminal=True)
