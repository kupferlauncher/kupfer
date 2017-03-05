__kupfer_name__ = _("Window List")
__kupfer_sources__ = ("WindowsSource", "WorkspacesSource", )
__description__ = _("All windows on all workspaces")
__version__ = "2017.2"
__author__ = ""

from gi.repository import Wnck

from kupfer.objects import Leaf, Action, Source, NotAvailableError
from kupfer.weaklib import gobject_connect_weakly


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
            return ""
        _nr, name = workspace.get_number(), workspace.get_name()
        # TRANS: Window on (Workspace name), window description
        return _("Window on %(wkspc)s") % {"wkspc": name}

    def get_icon_name(self):
        return "kupfer-window"

class FrontmostWindow (WindowLeaf):
    qf_id = "frontwindow"
    def __init__(self):
        WindowLeaf.__init__(self, None, _("Frontmost Window"))

    # HACK: Make self.object a property
    # so that this leaf is *not* immutable
    def _set_object(self, obj):
        pass
    def _get_object(self):
        scr = Wnck.Screen.get_default()
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
        scr = Wnck.Screen.get_default()
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
        super().__init__(name)
    def wants_context(self):
        return True
    def activate (self, leaf, ctx):
        window = leaf.object
        workspace = window.get_workspace()
        time = ctx.environment.get_timestamp()
        workspace.activate(time)
        window.activate(time)
    def get_description(self):
        return _("Jump to this window's workspace and focus")
    def get_icon_name(self):
        return "go-jump"

class WindowMoveToWorkspace (Action):
    def __init__(self):
        Action.__init__(self, _("Move To..."))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj, ctx):
        window = leaf.object
        workspace = iobj.object
        window.move_to_workspace(workspace)
        time = ctx.environment.get_timestamp()
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

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        time = self._get_time(ctx) if self.time else None
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
    def _get_time(cls, ctx):
        # @time will be != 0 if we are "inside"
        # a current gtk event
        return ctx.environment.get_timestamp()

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

    def activate(self, leaf, ctx):
        if self.predicate(leaf.object):
            # only use time on the disable action
            time = self._get_time(ctx) if self.time else None
            self._perform_action(self.uaction, leaf, time)
        else:
            self._perform_action(self.action, leaf)

class WindowsSource (Source):
    def __init__(self, name=_("Window List")):
        super().__init__(name)

    def initialize(self):
        # "preload" windows: Ask for them early
        # since the first call "primes" the event loop
        # and always comes back empty
        screen = Wnck.Screen.get_default()
        if screen is not None:
            screen.get_windows_stacked()

    def is_dynamic(self):
        return True

    def get_items(self):
        # wnck should be "primed" now to return the true list
        screen = Wnck.Screen.get_default()
        if screen is None:
            self.output_debug("Environment not supported")
            return
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
        return "kupfer-window"
    def provides(self):
        yield WindowLeaf

class Workspace (Leaf):
    def get_actions(self):
        yield ActivateWorkspace()
    def repr_key(self):
        return self.object.get_number()
    def get_icon_name(self):
        return "kupfer-window"
    def get_description(self):
        screen = Wnck.Screen.get_default()
        if screen:
            n_windows = sum([1 for w in screen.get_windows()
                            if w.get_workspace() == self.object])

            w_msg = (ngettext("%d window", "%d windows", n_windows) % n_windows)

            active_wspc = screen.get_active_workspace()
            if active_wspc == self.object:
                return _("Active workspace") + " (%s)" % w_msg
            if n_windows:
                return "(%s)" % w_msg
        return None

class ActivateWorkspace (Action):
    action_accelerator = "o"
    rank_adjust = 5
    def __init__(self):
        Action.__init__(self, _("Go To"))

    def wants_context(self):
        return True
    def activate (self, leaf, ctx):
        workspace = leaf.object
        time = ctx.environment.get_timestamp()
        workspace.activate(time)

    def get_description(self):
        return _("Jump to this workspace")
    def get_icon_name(self):
        return "go-jump"


class WorkspacesSource (Source):
    source_use_cache = False

    def __init__(self):
        super().__init__(_("Workspaces"))

    def initialize(self):
        screen = Wnck.Screen.get_default()
        if screen is not None:
            screen.get_workspaces()
            gobject_connect_weakly(screen, "workspace-created", self._changed)
            gobject_connect_weakly(screen, "workspace-destroyed", self._changed)

    def _changed(self, screen, workspace):
        self.mark_for_update()

    def get_items(self):
        # wnck should be "primed" now to return the true list
        screen = Wnck.Screen.get_default()
        if screen is None:
            return
        for wspc in screen.get_workspaces():
            yield Workspace(wspc, wspc.get_name())

    def get_icon_name(self):
        return "kupfer-window"
    def provides(self):
        yield Workspace

