import gobject
import gtk
import wnck

from kupfer.objects import Leaf, Action, Source

def wait_gtk():
	while gtk.events_pending():
		gtk.main_iteration()

class WindowLeaf (Leaf):
	def get_actions(self):
		win = self.object
		if not win.is_active():
			yield WindowAction("Activate", time=True)
		yield WindowActivateWorkspace()
		if win.is_shaded():
			yield WindowAction("Unshade")
		else:
			yield WindowAction("Shade")
		if win.is_minimized():
			yield WindowAction("Unminimize", time=True)
		else:
			yield WindowAction("Minimize")
		if win.is_maximized():
			yield WindowAction("Unmaximize")
		else:
			yield WindowAction("Maximize")
		if win.is_maximized_vertically():
			yield WindowAction("Unmaximize vertically", action="unmaximize_vertically")
		else:
			yield WindowAction("Maximize vertically", action="maximize_vertically")
		yield WindowAction("Close", time=True)

	def get_description(self):
		workspace = self.object.get_workspace()
		nr, name = workspace.get_number(), workspace.get_name()
		return "Window %s on %s" % (self, name)

	def get_icon_name(self):
		return "gnome-window-manager"

class WindowActivateWorkspace (Action):
	def __init__(self, name="Go to Workspace"):
		super(WindowActivateWorkspace, self).__init__(name)
	def activate (self, leaf):
		window = leaf.object
		workspace = window.get_workspace()
		time = gtk.get_current_event_time()
		workspace.activate(time)
		window.activate(time)
	def get_description(self):
		return "Go to this window's workspace and focus"

class WindowAction (Action):
	def __init__(self, name, action=None, time=False):
		super(Action, self).__init__(name)
		if not action: action = name.lower()
		self.action = action
		self.time = time
	def activate(self, leaf):
		window = leaf.object
		time = gtk.get_current_event_time()
		def make_call():
			call = window.__getattribute__(self.action)
			if self.time:
				return lambda: call(time)
			else:
				return call
		# Make sure other things happen first
		wait_gtk()
		gobject.idle_add(make_call())

class WindowsSource (Source):
	def __init__(self, name="Windows"):
		super(WindowsSource, self).__init__(name)

	def is_dynamic(self):
		return True
	def get_items(self):
		screen = wnck.screen_get_default()
		# wait a bit -- to get the window list
		wait_gtk()
		for win in reversed(screen.get_windows_stacked()):
			if not win.is_skip_tasklist():
				name, app = (win.get_name(), win.get_application().get_name())
				if name != app:
					name = "%s (%s)" % (name, app)
				yield WindowLeaf(win, name)

	def get_description(self):
		return "All windows on all workspaces"
	def get_icon_name(self):
		return "gnome-window-manager"

