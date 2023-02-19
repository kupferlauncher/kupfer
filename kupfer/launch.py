from __future__ import annotations

import os
import pickle
import typing as ty
from collections import defaultdict
from pathlib import Path
from time import time

from gi.repository import Gdk, Gio, GLib

try:
    from gi.repository import Wnck

    Wnck.set_client_type(Wnck.ClientType.PAGER)
    if "WAYLAND_DISPLAY" in os.environ:
        Wnck.Screen.get_default = lambda *x: None

except ImportError as e:
    from kupfer.support import pretty

    pretty.print_info(__name__, "Disabling window tracking:", e)
    Wnck = None

from kupfer import config, desktop_launch, terminal

## NOTE: SpawnError  *should* be imported from this module
from kupfer.desktop_launch import SpawnError  # pylint: disable=unused-import
from kupfer.support import pretty, scheduler
from kupfer.ui import uievents

_DEFAULT_ASSOCIATIONS = {
    "evince": "Document Viewer",
    "file-roller": "File Roller",
    # "gedit" : "Text Editor",
    "gnome-keyring-manager": "Keyring Manager",
    "nautilus-browser": "File Manager",
    "rhythmbox": "Rhythmbox Music Player",
}


def application_id(
    app_info: Gio.AppInfo, desktop_file: str | None = None
) -> str:
    """Return an application id (string) for GAppInfo @app_info"""
    app_id = app_info.get_id() or desktop_file or ""
    app_id = app_id.removesuffix(".desktop")
    return app_id


def launch_application(
    app_info: Gio.AppInfo,
    files: ty.Iterable[str] = (),
    uris: ty.Iterable[str] = (),
    paths: ty.Iterable[str] = (),
    track: bool = True,
    activate: bool = True,
    desktop_file: str | None = None,
    screen: Gdk.Screen | None = None,
) -> bool:
    """
    Launch @app_rec correctly, using a startup notification

    you may pass in either a list of Gio.Files in @files, or
    a list of @uris or @paths

    if @track, it is a user-level application
    if @activate, activate rather than start a new version

    @app_rec is either an GAppInfo or (GAppInfo, desktop_file_path) tuple

    Raises SpawnError on failed program start.
    """
    assert app_info
    assert not (
        bool(paths) and bool(uris)
    ), "either paths or uris must be given: " + repr((paths, uris))

    svc = get_applications_matcher_service()
    app_id = application_id(app_info, desktop_file)

    if activate and svc.application_is_running(app_id):
        svc.application_to_front(app_id)
        return True

    launch_callback = None
    if track:
        # An launch callback closure for the @app_id
        def app_launch_callback(argv, pid, _notify_id, _files, _timestamp):
            if not terminal.is_known_terminal_executable(argv[0]):
                svc.launched_application(app_id, pid)

        launch_callback = app_launch_callback

    if paths:
        files = [Gio.File.new_for_path(p) for p in paths]

    if uris:
        files = [Gio.File.new_for_uri(p) for p in uris]

    desktop_launch.launch_app_info(
        app_info,
        files,
        timestamp=uievents.current_event_time(),
        desktop_file=desktop_file,
        launch_cb=launch_callback,
        screen=screen,
    )
    return True


def application_is_running(app_id: str) -> bool:
    svc = get_applications_matcher_service()
    return svc.application_is_running(app_id)


def application_close_all(app_id: str) -> None:
    svc = get_applications_matcher_service()
    svc.application_close_all(app_id)


class ApplicationsMatcherService(pretty.OutputMixin):
    """Handle launching applications and see if they still run.
    This is a learning service, since we have no first-class application
    object on the Linux desktop
    """

    _instance: ApplicationsMatcherService | None = None

    @classmethod
    def instance(cls) -> ApplicationsMatcherService:
        if cls._instance is None:
            cls._instance = ApplicationsMatcherService()

        return cls._instance

    def __init__(self):
        self.register: dict[str, "Wnck.Window"] = {}
        self._get_wnck_screen_windows_stacked()
        scheduler.get_scheduler().connect("finish", self._finish)
        self._load()

    @classmethod
    def _get_wnck_screen_windows_stacked(cls) -> ty.Iterable["Wnck.Window"]:
        if Wnck:
            if screen := Wnck.Screen.get_default():
                return screen.get_windows_stacked()  # type: ignore

        return ()

    def _get_filename(self) -> str:
        # Version 1: Up to incl v203
        # Version 2: Do not track terminals
        version = 2
        return os.path.join(
            config.get_cache_home() or "",
            f"application_identification_v{version}.pickle",
        )

    def _load(self) -> None:
        reg = self._unpickle_register(self._get_filename())
        self.register = reg or _DEFAULT_ASSOCIATIONS
        # pretty-print register to debug
        if self.register:
            self.output_debug("Learned the following applications")
            items = "\n".join(
                f"  {k:<30} : {v}" for k, v in self.register.items()
            )
            self.output_debug(f"\n{{\n{items}\n}}")

    def _finish(self, _sched: ty.Any) -> None:
        self._pickle_register(self.register, self._get_filename())

    def _unpickle_register(self, pickle_file: str) -> ty.Any:
        try:
            source = pickle.loads(Path(pickle_file).read_bytes())
            assert isinstance(source, dict), "Stored object not a dict"
            self.output_debug(f"Reading from {pickle_file}")
            return source
        except OSError:
            pass
        except (pickle.PickleError, Exception) as exc:
            self.output_info(f"Error loading {pickle_file}: {exc}")

        return None

    def _pickle_register(self, reg: ty.Any, pickle_file: str) -> bool:
        self.output_debug(f"Saving to {pickle_file}")
        Path(pickle_file).write_bytes(
            pickle.dumps(reg, pickle.HIGHEST_PROTOCOL)
        )
        return True

    def _store(self, app_id: str, window: "Wnck.Window") -> None:
        # FIXME: Store the 'res_class' name?
        application = window.get_application()
        res_class = window.get_class_group().get_res_class()
        store_name = application.get_name()
        self.register[app_id] = res_class
        self.output_debug(
            "storing application",
            app_id,
            "as",
            store_name,
            "res_class",
            res_class,
        )

    def _has_match(self, app_id: str | None) -> bool:
        if not app_id:
            return False

        return app_id in self.register

    def _is_match(self, app_id: str, window: "Wnck.Window") -> bool:
        application = window.get_application()
        res_class = window.get_class_group().get_res_class()
        reg_name = self.register.get(app_id)
        if reg_name and reg_name in (application.get_name(), res_class):
            return True

        if app_id in (application.get_name().lower(), res_class.lower()):
            return True

        return False

    def launched_application(self, app_id: str, pid: int) -> None:
        if self._has_match(app_id):
            return

        timeout = time() + 15
        GLib.timeout_add_seconds(
            2, self._find_application, app_id, pid, timeout
        )
        # and once later
        GLib.timeout_add_seconds(
            30, self._find_application, app_id, pid, timeout
        )

    def _find_application(self, app_id: str, pid: int, timeout: float) -> bool:
        if self._has_match(app_id):
            return False

        # self.output_debug("Looking for window for application", app_id)
        for win in self._get_wnck_screen_windows_stacked():
            app = win.get_application()
            app_pid = app.get_pid() or win.get_pid()
            if app_pid == pid:
                self._store(app_id, win)
                return False

        return time() <= timeout

    def application_name(self, app_id: str | None) -> str | None:
        if not self._has_match(app_id):
            return None

        return self.register[app_id]  # type: ignore

    def application_is_running(self, app_id: str) -> bool:
        for win in self._get_wnck_screen_windows_stacked():
            if (
                win.get_application()
                and self._is_match(app_id, win)
                and win.get_window_type() == Wnck.WindowType.NORMAL
            ):
                return True

        return False

    def _get_application_windows(
        self, app_id: str
    ) -> ty.Iterator["Wnck.Window"]:
        if not Wnck:
            return

        for win in self._get_wnck_screen_windows_stacked():
            if (
                win.get_application()
                and self._is_match(app_id, win)
                and win.get_window_type() == Wnck.WindowType.NORMAL
            ):
                yield win

    def application_to_front(self, app_id: str) -> None:
        application_windows = list(self._get_application_windows(app_id))
        if not application_windows:
            return

        etime = uievents.current_event_time()
        # if True, focus app's all windows on the same workspace
        # if False, focus only one window (in cyclical manner)
        focus_all = True
        if focus_all:
            self._to_front_application_style(application_windows, etime)
            return

        self._to_front_single(application_windows, etime)

    def _to_front_application_style(
        self, application_windows: list["Wnck.Window"], evttime: int
    ) -> None:
        workspaces: dict[Wnck.Workspace, list[Wnck.Window]] = defaultdict(list)
        cur_screen = application_windows[0].get_screen()
        cur_workspace = cur_screen.get_active_workspace()

        ## get all visible windows in stacking order
        vis_windows = [
            win
            for win in self._get_wnck_screen_windows_stacked()
            if (
                win.get_window_type() == Wnck.WindowType.NORMAL
                and win.is_visible_on_workspace(cur_workspace)
            )
        ]

        ## sort windows into "bins" by workspace
        for win in application_windows:
            if win.get_window_type() == Wnck.WindowType.NORMAL:
                wspc = win.get_workspace() or cur_workspace
                workspaces[wspc].append(win)

        cur_wspc_windows = workspaces[cur_workspace]
        # make a rotated workspace list, with current workspace first
        all_workspaces = cur_screen.get_workspaces()
        all_workspaces.pop(cur_workspace.get_number())
        # check if the application's window on current workspace
        # are the topmost
        focus_windows = []
        if cur_wspc_windows and set(
            vis_windows[-len(cur_wspc_windows) :]
        ) != set(cur_wspc_windows):
            focus_windows = cur_wspc_windows
            ## if the topmost window is already active, take another
            if focus_windows[-1] == vis_windows[-1]:
                focus_windows.pop()
        else:
            # all windows are focused, find on next workspace
            for wspc in all_workspaces[1:]:
                if focus_windows := workspaces[wspc]:
                    break
            else:
                # no windows on other workspaces, so we rotate among
                # the local ones
                focus_windows = cur_wspc_windows[:1]

        self._focus_windows(focus_windows, evttime)

    def _to_front_single(
        self, application_windows: list["Wnck.Window"], evttime: int
    ) -> None:
        # bring the first window to front
        for window in application_windows:
            self._focus_windows([window], evttime)
            return

    def _focus_windows(
        self, windows: list["Wnck.Window"], evttime: int
    ) -> None:
        for window in windows:
            # we special-case the desktop
            # only show desktop if it's the only window
            if window.get_name() == "x-nautilus-desktop":
                if len(windows) == 1:
                    if screen := Wnck.Screen.get_default():
                        screen.toggle_showing_desktop(True)
                else:
                    continue

            if wspc := window.get_workspace():
                wspc.activate(evttime)

            window.activate_transient(evttime)

    def application_close_all(self, app_id: str) -> None:
        application_windows = self._get_application_windows(app_id)
        evttime = uievents.current_event_time()
        for win in application_windows:
            if not win.is_skip_tasklist():
                win.close(evttime)


# Get the (singleton) ApplicationsMatcherService"
get_applications_matcher_service = ApplicationsMatcherService.instance
