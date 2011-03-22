__kupfer_name__ = _("Window List")
__kupfer_sources__ = ("WindowsSource", "WorkspacesSource", )
__description__ = _("All windows on all workspaces")
__version__ = "2010-01-08"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import gtk
import wnck

from kupfer.objects import Leaf, Action, Source
from kupfer.ui import keybindings
from kupfer.weaklib import gobject_connect_weakly
from kupfer.obj.helplib import PicklingHelperMixin


def _get_current_event_time():
	return gtk.get_current_event_time() or keybindings.get_current_event_time()

class WindowLeaf (Leaf):
	def get_actions(self):
		yield WindowActivateWorkspace()
		yield WindowMoveToWorkspace()
		yield WindowAction(_("Activate"), "activate", time=True)

		W = self.object
		T = type(W)
		yield ToggleAction(_("Shade"), _("Unshade"),
				"shade", "unshade",
				W.is_shaded(), T.is_shaded)
		yield ToggleAction(_("Minimize"), _("Unminimize"),
				"minimize", "unminimize",
				W.is_minimized(), T.is_minimized,
				time=True, icon="list-remove")
		yield ToggleAction(_("Maximize"), _("Unmaximize"),
				"maximize", "unmaximize",
				W.is_maximized(), T.is_maximized,
				icon="list-add")
		yield ToggleAction(_("Maximize Vertically"), _("Unmaximize Vertically"),
				"maximize_vertically", "unmaximize_vertically",
				W.is_maximized_vertically(), T.is_maximized_vertically,
				icon="list-add")
		yield WindowAction(_("Close"), "close", time=True, icon="window-close")

	def is_valid(self):
		return self.object and self.object.get_xid()

	def get_description(self):
		workspace = self.object.get_workspace()
		if not workspace:
			return u""
		nr, name = workspace.get_number(), workspace.get_name()
		# TRANS: Window on (Workspace name), window description
		return _("Window on %(wkspc)s") % {"wkspc": name}

	def get_icon_name(self):
		return "gnome-window-manager"

class FrontmostWindow (WindowLeaf):
	qf_id = "frontwindow"
	def __init__(self):
		WindowLeaf.__init__(self, None, _("Frontmost Window"))

	# HACK: Make self.object a property
	# so that this leaf is *not* immutable
	def _set_object(self, obj):
		pass
	def _get_object(self):
		scr = wnck.screen_get_default()
		active = scr.get_active_window() or scr.get_previously_active_window()
		# FIXME: Ignore Kupfer's main window reliably
		if active and active.get_application().get_name() != "kupfer.py":
			if not active.is_skip_tasklist():
				return active
		wspc = scr.get_active_workspace()
		for win in reversed(scr.get_windows_stacked()):
			if not win.is_skip_tasklist():
				if win.is_on_workspace(wspc):
					return win
	object = property(_get_object, _set_object)

	def repr_key(self):
		return ""

	def get_description(self):
		return self.object and self.object.get_name()

class NextWindow (WindowLeaf):
	qf_id = "nextwindow"
	def __init__(self):
		WindowLeaf.__init__(self, None, _("Next Window"))

	def _set_object(self, obj):
		pass
	def _get_object(self):
		scr = wnck.screen_get_default()
		wspc = scr.get_active_workspace()
		for win in scr.get_windows_stacked():
			if not win.is_skip_tasklist():
				if win.is_on_workspace(wspc):
					return win
	object = property(_get_object, _set_object)

	def repr_key(self):
		return ""

	def get_description(self):
		return self.object and self.object.get_name()

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
		return "go-jump"

class WindowMoveToWorkspace (Action):
	def __init__(self):
		Action.__init__(self, _("Move To..."))

	def activate(self, leaf, iobj):
		window = leaf.object
		workspace = iobj.object
		window.move_to_workspace(workspace)
		time = _get_current_event_time()
		workspace.activate(time)
		window.activate(time)

	def requires_object(self):
		return True
	def object_types(self):
		yield Workspace
	def object_source(self, for_item=None):
		return WorkspacesSource()

	def valid_object(self, iobj, for_item):
		window = for_item.object
		return not window.is_on_workspace(iobj.object)

	def get_icon_name(self):
		return "forward"

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
		yield FrontmostWindow()
		yield NextWindow()
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

class Workspace (Leaf):
	def get_actions(self):
		yield ActivateWorkspace()
	def repr_key(self):
		return self.object.get_number()
	def get_icon_name(self):
		return "gnome-window-manager"
	def get_description(self):
		screen = wnck.screen_get_default()
		if screen:
			wspc = screen.get_active_workspace()
			if wspc == self.object:
				return _("Active workspace")

class ActivateWorkspace (Action):
	rank_adjust = 5
	def __init__(self):
		Action.__init__(self, _("Go To"))

	def activate (self, leaf):
		workspace = leaf.object
		time = _get_current_event_time()
		workspace.activate(time)

	def get_description(self):
		return _("Jump to this workspace")
	def get_icon_name(self):
		return "go-jump"


class WorkspacesSource (Source, PicklingHelperMixin):
	def __init__(self):
		Source.__init__(self, _("Workspaces"))
		screen = wnck.screen_get_default()
		screen.get_workspaces()

	def pickle_prepare(self):
		self.mark_for_update()

	def initialize(self):
		screen = wnck.screen_get_default()
		gobject_connect_weakly(screen, "workspace-created", self._changed)
		gobject_connect_weakly(screen, "workspace-destroyed", self._changed)

	def _changed(self, screen, workspace):
		self.mark_for_update()

	def get_items(self):
		# wnck should be "primed" now to return the true list
		screen = wnck.screen_get_default()
		for wspc in screen.get_workspaces():
			yield Workspace(wspc, wspc.get_name())

	def get_icon_name(self):
		return "gnome-window-manager"
	def provides(self):
		yield Workspace

