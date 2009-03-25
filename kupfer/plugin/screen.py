from kupfer.objects import Leaf, Action, Source
from kupfer import utils

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
		return "%s session %s (%s) created %s" % (status, name, pid, time)

	def get_icon_name(self):
		return "gnome-window-manager"

class ScreenSessionsSource (Source):
	"""Source for GNU Screen sessions"""
	def __init__(self):
		super(ScreenSessionsSource, self).__init__("Screen sessions")
	def is_dynamic(self):
		return True
	def get_items(self):
		for pid, name, time, status in screen_sessions_infos():
			yield ScreenSession(pid, name)

	def get_description(self):
		return "Active GNU Screen sessions"
	def get_icon_name(self):
		return "terminal"

class AttachScreen (Action):
	"""
	"""
	def __init__(self):
		name = "Attach"
		super(AttachScreen, self).__init__(name)
	def activate(self, leaf):
		import gio
		pid = leaf.object
		action = "screen -x -R %s" % pid
		item = gio.AppInfo(action, "GNU Screen session", gio.APP_INFO_CREATE_NEEDS_TERMINAL)
		utils.launch_app(item)
