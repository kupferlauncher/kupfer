from kupfer.objects import Leaf, Action, Source

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
		pid = leaf.object
		action = "/usr/bin/screen -x -R %s" % pid
		import gnomedesktop as gd
		item = gd.DesktopItem()
		item.set_entry_type(gd.TYPE_APPLICATION)
		item.set_string(gd.KEY_NAME, self.name)
		item.set_string(gd.KEY_EXEC, action)
		item.set_boolean(gd.KEY_TERMINAL, True)
		item.launch([], 0)
