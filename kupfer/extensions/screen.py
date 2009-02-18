
from kupfer.objects import Leaf, Action, Source

class ScreenSession (Leaf):
	"""Represented object is the session pid as string"""
	def get_actions(self):
		return (AttachScreen(),)
	def get_icon_name(self):
		return "gnome-window-manager"

class ScreenSessionsSource (Source):
	"""Source for GNU Screen sessions"""
	def __init__(self):
		super(ScreenSessionsSource, self).__init__("Screen sessions")
	def is_dynamic(self):
		return True
	def get_items(self):
		from os import popen
		pipe = popen("screen -list")
		output = pipe.read()
		sessions = []
		for line in output.splitlines():
			fields = line.split("\t")
			if len(fields) == 4:
				empty, pidname, time, status = fields
				pid, name = pidname.split(".", 1)
				sessions.append(ScreenSession(pid, name))
		return sessions
	def get_icon_name(self):
		return "terminal"

class AttachScreen (Action):
	"""
	Execute executable file (FileLeaf)
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
