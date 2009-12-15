import gobject
import gtk

from kupfer.objects import Leaf, Action, Source

__kupfer_name__ = _("Window List")
__kupfer_sources__ = ("WindowsSource", )
__description__ = _("All windows on all workspaces")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

# "Critical" imports have to be imported past the plugin information
# variables in Kupfer, else the plugin can't be shown if the import fails
import wnck

class WindowLeaf (Leaf):
	def get_actions(self):
		win = self.object
		yield WindowActivateWorkspace()
		if not win.is_active():
			yield WindowAction(_("Activate"), action="activate", time=True)
		if win.is_shaded():
			yield WindowAction(_("Unshade"), action="unshade")
		else:
			yield WindowAction(_("Shade"), action="shade")
		if win.is_minimized():
			yield WindowAction(_("Unminimize"), action="unminimize", time=True, icon="gtk-remove")
		else:
			yield WindowAction(_("Minimize"), action="minimize", icon="gtk-remove")
		if win.is_maximized():
			yield WindowAction(_("Unmaximize"), action="unmaximize", icon="gtk-add")
		else:
			yield WindowAction(_("Maximize"), action="maximize", icon="gtk-add")
		if win.is_maximized_vertically():
			yield WindowAction(_("Unmaximize Vertically"),
					action="unmaximize_vertically", icon="gtk-add")
		else:
			yield WindowAction(_("Maximize Vertically"),
					action="maximize_vertically", icon="gtk-add")
		yield WindowAction(_("Close"), action="close", time=True, icon="gtk-close")

	def get_description(self):
		workspace = self.object.get_workspace()
		nr, name = workspace.get_number(), workspace.get_name()
		# TRANS: Window on (Workspace name), window description
		return _("Window on %(wkspc)s") % {"wkspc": name}

	def get_icon_name(self):
		return "gnome-window-manager"

class WindowActivateWorkspace (Action):
	def __init__(self, name=_("Go To")):
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

	def repr_key(self):
		return self.action

	def activate(self, leaf):
		window = leaf.object
		action_method = getattr(window, self.action)
		if self.time:
			# @time will be != 0 if we are "inside"
			# a current gtk event
			time = gtk.get_current_event_time()
			action_method(time)
		else:
			action_method()

	def get_icon_name(self):
		if not self.icon_name:
			return super(WindowAction, self).get_icon_name()
		return self.icon_name

class WindowsSource (Source):
	def __init__(self, name=_("Window List")):
		super(WindowsSource, self).__init__(name)
		# "preload" windows: Ask for them early
		# since the first call "primes" the event loop
		# and always comes back empty
		screen = wnck.screen_get_default()
		screen.get_windows_stacked()

	def is_dynamic(self):
		return True
	def get_items(self):
		# wnck should be "primed" now to return the true list
		screen = wnck.screen_get_default()
		for win in reversed(screen.get_windows_stacked()):
			if not win.is_skip_tasklist():
				name, app = (win.get_name(), win.get_application().get_name())
				if name != app and app not in name:
					name = "%s (%s)" % (name, app)
				yield WindowLeaf(win, name)

	def get_description(self):
		return _("All windows on all workspaces")
	def get_icon_name(self):
		return "gnome-window-manager"
	def provides(self):
		yield WindowLeaf

