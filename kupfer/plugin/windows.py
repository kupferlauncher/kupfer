import gtk

from kupfer.objects import Leaf, Action, Source
from kupfer.ui import keybindings

__kupfer_name__ = _("Window List")
__kupfer_sources__ = ("WindowsSource", )
__description__ = _("All windows on all workspaces")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

# "Critical" imports have to be imported past the plugin information
# variables in Kupfer, else the plugin can't be shown if the import fails
import wnck

def _get_current_event_time():
	return gtk.get_current_event_time() or keybindings.get_current_event_time()

class WindowLeaf (Leaf):
	def get_actions(self):
		yield WindowActivateWorkspace()
		yield WindowAction(_("Activate"), "activate", time=True)

		W = self.object
		T = type(W)
		yield ToggleAction(_("Shade"), _("Unshade"),
				"shade", "unshade",
				W.is_shaded(), T.is_shaded)
		yield ToggleAction(_("Minimize"), _("Unminimize"),
				"minimize", "unminimize",
				W.is_minimized(), T.is_minimized,
				time=True, icon="gtk-remove")
		yield ToggleAction(_("Maximize"), _("Unmaximize"),
				"maximize", "unmaximize",
				W.is_maximized(), T.is_maximized,
				icon="gtk-add")
		yield ToggleAction(_("Maximize Vertically"), _("Unmaximize Vertically"),
				"maximize_vertically", "unmaximize_vertically",
				W.is_maximized_vertically(), T.is_maximized_vertically,
				icon="gtk-add")
		yield WindowAction(_("Close"), "close", time=True, icon="gtk-close")

	def get_description(self):
		workspace = self.object.get_workspace()
		nr, name = workspace.get_number(), workspace.get_name()
		# TRANS: Window on (Workspace name), window description
		return _("Window on %(wkspc)s") % {"wkspc": name}

	def get_icon_name(self):
		return "gnome-window-manager"

class FrontmostWindow (WindowLeaf):
	qf_id = "frontwindow"
	def __init__(self, obj, name):
		WindowLeaf.__init__(self, obj, _("Frontmost Window"))
		self.window_name = name

	def repr_key(self):
		return ""

	def get_description(self):
		return self.window_name

class WindowActivateWorkspace (Action):
	def __init__(self, name=_("Go To")):
		super(WindowActivateWorkspace, self).__init__(name)
	def activate (self, leaf):
		window = leaf.object
		workspace = window.get_workspace()
		time = _get_current_event_time()
		workspace.activate(time)
		window.activate(time)
	def get_description(self):
		return _("Jump to this window's workspace and focus")
	def get_icon_name(self):
		return "gtk-jump-to-ltr"

class WindowAction (Action):
	def __init__(self, name, action, time=False, icon=None):
		super(Action, self).__init__(name)
		if not action: action = name.lower()
		self.action = action
		self.time = time
		self.icon_name = icon

	def repr_key(self):
		return self.action

	def activate(self, leaf):
		time = self._get_time() if self.time else None
		self._perform_action(self.action, leaf, time)

	@classmethod
	def _perform_action(cls, action_attr, leaf, time=None):
		window = leaf.object
		action_method = getattr(window, action_attr)
		if time is not None:
			action_method(time)
		else:
			action_method()

	@classmethod
	def _get_time(cls):
		# @time will be != 0 if we are "inside"
		# a current gtk event
		return _get_current_event_time()

	def get_icon_name(self):
		if not self.icon_name:
			return super(WindowAction, self).get_icon_name()
		return self.icon_name

class ToggleAction (WindowAction):
	"""A toggle action, performing the enable / disable action as needed,
	for example minimize/unminimize.

	@istate: Initial state
	@predicate: Callable for state taking the window object as only argument
	"""
	def __init__(self, ename, uname, eaction, uaction, istate, predicate,
			time=False, icon=None):
		name = uname if istate else ename
		WindowAction.__init__(self, name, eaction, time=time, icon=icon)
		self.predicate = predicate
		self.uaction = uaction

	def activate(self, leaf):
		if self.predicate(leaf.object):
			# only use time on the disable action
			time = self._get_time() if self.time else None
			self._perform_action(self.uaction, leaf, time)
		else:
			self._perform_action(self.action, leaf)

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
		front = True
		for win in reversed(screen.get_windows_stacked()):
			if not win.is_skip_tasklist():
				name, app = (win.get_name(), win.get_application().get_name())
				if name != app and app not in name:
					name = "%s (%s)" % (name, app)
				if front:
					yield FrontmostWindow(win, name)
					front = False
				yield WindowLeaf(win, name)

	def get_description(self):
		return _("All windows on all workspaces")
	def get_icon_name(self):
		return "gnome-window-manager"
	def provides(self):
		yield WindowLeaf

