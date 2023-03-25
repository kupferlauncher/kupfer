__kupfer_name__ = _("Window List")
__kupfer_sources__ = (
    "WindowsSource",
    "WorkspacesSource",
)
__description__ = _("All windows on all workspaces")
__version__ = "2020-04-14"
__author__ = ""

import typing as ty

from gi.repository import Wnck

from kupfer.obj import Action, Leaf, Source
from kupfer.support import system, weaklib

if ty.TYPE_CHECKING:
    from gettext import gettext as _
    from gettext import ngettext


def _get_window(xid):
    """Get wnck window by xid."""
    if not xid:
        return None

    if scr := Wnck.Screen.get_default():
        for wnd in scr.get_windows():
            if wnd.get_xid() == xid:
                return wnd

    return None


def _get_workspace(idx):
    """Get wnck workspacke by its number."""
    if scr := Wnck.Screen.get_default():
        return scr.get_workspace(idx)

    return None


class WindowLeaf(Leaf):
    # object = window xid

    def get_actions(self):
        yield WindowActivateWorkspace()
        yield WindowMoveToWorkspace()
        yield WindowAction(_("Activate"), "activate", time=True)

        win = _get_window(self.object)
        if not win:
            return

        win_type = type(win)
        yield ToggleAction(
            _("Shade"),
            _("Unshade"),
            "shade",
            "unshade",
            win.is_shaded(),
            win_type.is_shaded,
        )
        yield ToggleAction(
            _("Minimize"),
            _("Unminimize"),
            "minimize",
            "unminimize",
            win.is_minimized(),
            win_type.is_minimized,
            time=True,
            icon="list-remove",
        )
        yield ToggleAction(
            _("Maximize"),
            _("Unmaximize"),
            "maximize",
            "unmaximize",
            win.is_maximized(),
            win_type.is_maximized,
            icon="list-add",
        )
        yield ToggleAction(
            _("Maximize Vertically"),
            _("Unmaximize Vertically"),
            "maximize_vertically",
            "unmaximize_vertically",
            win.is_maximized_vertically(),
            win_type.is_maximized_vertically,
            icon="list-add",
        )
        yield WindowAction(_("Close"), "close", time=True, icon="window-close")

    def is_valid(self):
        wnd = _get_window(self.object)
        return wnd and wnd.get_xid() == self.object

    def get_description(self):
        wnd = _get_window(self.object)
        if not wnd:
            return ""

        workspace = wnd.get_workspace()
        if not workspace:
            return ""

        _nr, name = workspace.get_number(), workspace.get_name()
        # TRANS: Window on (Workspace name), window description
        return _("Window on %(wkspc)s") % {"wkspc": name}

    def get_icon_name(self):
        return "kupfer-window"


class FrontmostWindow(WindowLeaf):
    qf_id = "frontwindow"

    def __init__(self):
        WindowLeaf.__init__(self, None, _("Frontmost Window"))

    # HACK: Make self.object a property
    # so that this leaf is *not* immutable
    def _set_object(self, obj):
        pass

    def _get_object(self):
        scr = Wnck.Screen.get_default()
        if scr is None:
            return None

        active = scr.get_active_window() or scr.get_previously_active_window()
        if active and active.get_application().get_name() not in (
            "kupfer.py",
            system.get_application_filename(),
        ):
            if not active.is_skip_tasklist():
                return active

        wspc = scr.get_active_workspace()
        for win in reversed(scr.get_windows_stacked()):
            if not win.is_skip_tasklist() and win.is_on_workspace(wspc):
                return win

        return None

    object = property(_get_object, _set_object)

    def repr_key(self):
        return None

    def get_description(self):
        return self.object and self.object.get_name()


class NextWindow(WindowLeaf):
    qf_id = "nextwindow"

    def __init__(self):
        WindowLeaf.__init__(self, None, _("Next Window"))

    def _set_object(self, obj):
        pass

    def _get_object(self):
        scr = Wnck.Screen.get_default()
        if scr is None:
            return None

        wspc = scr.get_active_workspace()
        for win in scr.get_windows_stacked():
            if not win.is_skip_tasklist() and win.is_on_workspace(wspc):
                return win

        return None

    object = property(_get_object, _set_object)

    def repr_key(self):
        return None

    def get_description(self):
        return self.object and self.object.get_name()


class WindowActivateWorkspace(Action):
    def __init__(self, name=_("Go To")):
        super().__init__(name)

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        window = _get_window(leaf.object)
        if not window:
            return

        workspace = window.get_workspace()
        time = ctx.environment.get_timestamp()
        workspace.activate(time)
        window.activate(time)

    def get_description(self):
        return _("Jump to this window's workspace and focus")

    def get_icon_name(self):
        return "go-jump"


class WindowMoveToWorkspace(Action):
    def __init__(self):
        Action.__init__(self, _("Move To..."))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        assert ctx

        window = _get_window(leaf.object)
        if not window:
            return

        workspace = _get_workspace(iobj.object)
        if not workspace:
            return

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
        window = _get_window(for_item.object)
        return window and window.get_workspace().get_number() != iobj.object

    def get_icon_name(self):
        return "forward"


class WindowAction(Action):
    def __init__(self, name, action, time=False, icon=None):
        super(Action, self).__init__(name)
        self.action = action or name.lower()
        self.time = time
        self.icon_name = icon

    def repr_key(self):
        return self.action

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        time = self._get_time(ctx) if self.time else None
        self._perform_action(self.action, leaf, time)

    @classmethod
    def _perform_action(cls, action_attr, leaf, time=None):
        window = _get_window(leaf.object)
        if not window:
            return

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
            return super().get_icon_name()

        return self.icon_name


class ToggleAction(WindowAction):
    """A toggle action, performing the enable / disable action as needed,
    for example minimize/unminimize.

    @istate: Initial state
    @predicate: Callable for state taking the window object as only argument
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        ename,
        uname,
        eaction,
        uaction,
        istate,
        predicate,
        time=False,
        icon=None,
    ):
        name = uname if istate else ename
        WindowAction.__init__(self, name, eaction, time=time, icon=icon)
        self.predicate = predicate
        self.uaction = uaction

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        wnd = _get_window(leaf.object)
        if not wnd:
            return

        if self.predicate(wnd):
            # only use time on the disable action
            time = self._get_time(ctx) if self.time else None
            self._perform_action(self.uaction, leaf, time)
        else:
            self._perform_action(self.action, leaf)


class WindowsSource(Source):
    def __init__(self, name=_("Window List")):
        super().__init__(name)

    def initialize(self):
        # "preload" windows: Ask for them early
        # since the first call "primes" the event loop
        # and always comes back empty
        if (screen := Wnck.Screen.get_default()) is not None:
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
                    name = f"{name} ({app})"

                yield WindowLeaf(win.get_xid(), name)

    def get_description(self):
        return _("All windows on all workspaces")

    def get_icon_name(self):
        return "kupfer-window"

    def provides(self):
        yield WindowLeaf


class Workspace(Leaf):
    # object = number
    def get_actions(self):
        yield ActivateWorkspace()

    def repr_key(self):
        return self.object

    def get_icon_name(self):
        return "kupfer-window"

    def get_description(self):
        screen = Wnck.Screen.get_default()
        if screen:
            n_windows = sum(
                1
                for w in screen.get_windows()
                if (wsp := w.get_workspace())
                and wsp.get_number() == self.object
            )

            w_msg = ngettext("%d window", "%d windows", n_windows) % n_windows

            active_wspc = screen.get_active_workspace()
            if active_wspc.get_number() == self.object:
                return _("Active workspace") + " (" + w_msg + ")"

            if n_windows:
                return f"({w_msg})"

        return None


class ActivateWorkspace(Action):
    action_accelerator = "o"
    rank_adjust = 5

    def __init__(self):
        Action.__init__(self, _("Go To"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        if workspace := _get_workspace(leaf.object):
            time = ctx.environment.get_timestamp()
            workspace.activate(time)

    def get_description(self):
        return _("Jump to this workspace")

    def get_icon_name(self):
        return "go-jump"


class WorkspacesSource(Source):
    source_use_cache = False

    def __init__(self):
        super().__init__(_("Workspaces"))

    def initialize(self):
        if (screen := Wnck.Screen.get_default()) is not None:
            screen.get_workspaces()
            weaklib.gobject_connect_weakly(
                screen, "workspace-created", self._changed
            )
            weaklib.gobject_connect_weakly(
                screen, "workspace-destroyed", self._changed
            )

    def _changed(self, screen, workspace):
        self.mark_for_update()

    def get_items(self):
        # wnck should be "primed" now to return the true list
        screen = Wnck.Screen.get_default()
        if screen is None:
            return

        for wspc in screen.get_workspaces():
            yield Workspace(wspc.get_number(), wspc.get_name())

    def get_icon_name(self):
        return "kupfer-window"

    def provides(self):
        yield Workspace
