import gobject
import gtk
import wnck

from kupfer.objects import Leaf, Action, Source

__kupfer_sources__ = ("WindowsSource", )

def wait_gtk():
	while gtk.events_pending():
		gtk.main_iteration()

class WindowLeaf (Leaf):
	def get_actions(self):
		win = self.object
		if not win.is_active():
			yield WindowAction(_("Activate"), time=True)
		yield WindowActivateWorkspace()
		if win.is_shaded():
			yield WindowAction(_("Unshade"))
		else:
			yield WindowAction(_("Shade"))
		if win.is_minimized():
			yield WindowAction(_("Unminimize"), time=True, icon="gtk-remove")
		else:
			yield WindowAction(_("Minimize"), icon="gtk-remove")
		if win.is_maximized():
			yield WindowAction(_("Unmaximize"), icon="gtk-add")
		else:
			yield WindowAction(_("Maximize"), icon="gtk-add")
		if win.is_maximized_vertically():
			yield WindowAction(_("Unmaximize vertically"),
					action="unmaximize_vertically", icon="gtk-add")
		else:
			yield WindowAction(_("Maximize vertically"),
					action="maximize_vertically", icon="gtk-add")
		yield WindowAction(_("Close"), time=True, icon="gtk-close")

	def get_description(self):
		workspace = self.object.get_workspace()
		nr, name = workspace.get_number(), workspace.get_name()
		return _("Window %(name)s on %(wkspc)s") % {"name": self, "wkspc": name}

	def get_icon_name(self):
		return "gnome-window-manager"

class WindowActivateWorkspace (Action):
	def __init__(self, name=_("Go to")):
		super(WindowActivateWorkspace, self).__init__(name)
	def activate (self, leaf):
		window = leaf.object
		workspace = window.get_workspace()
		time = gtk.get_current_event_time()
		workspace.activate(time)
		window.activate(time)
	def get_description(self):
		return _("Jump to this window's workspace and focus")
	def get_icon_name(self):
		return "gtk-jump-to-ltr"

class WindowAction (Action):
	def __init__(self, name, action=None, time=False, icon=None):
		super(Action, self).__init__(name)
		if not action: action = name.lower()
		self.action = action
		self.time = time
		self.icon_name = icon
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
	def get_icon_name(self):
		if not self.icon_name:
			return super(WindowAction, self).get_icon_name()
		return self.icon_name

class WindowsSource (Source):
	def __init__(self, name=_("Windows")):
		super(WindowsSource, self).__init__(name)

	def is_dynamic(self):
		return True
	def get_items(self):
		# wait a bit -- to get the window list
		# windows might come out empty, and you have to proc
		# the event loop to do it
		# wait_gtk()
		# but this si not allowed, since it might intefere with
		# the main program!
		screen = wnck.screen_get_default()
		for win in reversed(screen.get_windows_stacked()):
			if not win.is_skip_tasklist():
				name, app = (win.get_name(), win.get_application().get_name())
				if name != app:
					name = "%s (%s)" % (name, app)
				yield WindowLeaf(win, name)

	def get_description(self):
		return _("All windows on all workspaces")
	def get_icon_name(self):
		return "gnome-window-manager"

