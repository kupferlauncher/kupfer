from __future__ import annotations

import os
import pickle
import signal
import sys
import typing as ty
import urllib.parse
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from time import time

from gi.repository import Gdk, Gio, GLib, Gtk

from kupfer.support import pretty

try:
    from gi.repository import Wnck

    Wnck.set_client_type(Wnck.ClientType.PAGER)
    if "WAYLAND_DISPLAY" in os.environ:
        Wnck.Screen.get_default = lambda *_x: None

except ImportError as e:
    pretty.print_info(__name__, "Disabling window tracking:", e)
    Wnck = None

from kupfer import config, desktop_launch
from kupfer.core import settings

## NOTE: SpawnError  *should* be imported from this module TODO: check
# pylint: disable=unused-import
from kupfer.desktop_launch import SpawnError
from kupfer.support import fileutils, pretty, scheduler, system
from kupfer.ui import uievents

__all__ = (
    "AsyncCommand",
    "SpawnError",
    "application_close_all",
    "application_id",
    "application_is_running",
    "get_applications_matcher_service",
    "get_display_path_for_bytestring",
    "launch_application",
    "show_help_url",
    "show_url",
    "spawn_async",
    "spawn_async_notify_as",
    "spawn_async_raise",
    "spawn_in_terminal",
    "spawn_terminal",
)

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
    if not app_id:
        pretty.print_debug(
            __name__,
            "failed to get app_id",
            "app_info",
            app_info,
            "desktop_file",
            desktop_file,
        )

    return app_id.removesuffix(".desktop")


# pylint: disable=too-many-arguments
def launch_application(
    app_info: Gio.AppInfo,
    files: ty.Iterable[Gio.File] = (),
    uris: ty.Iterable[str] = (),
    paths: ty.Iterable[str] = (),
    track: bool = True,
    activate: bool = True,
    desktop_file: str | None = None,
    screen: Gdk.Screen | None = None,
    work_dir: str | None = None,
) -> bool:
    """Launch `app_rec` correctly, using a startup notification. You may pass
    inlist of `Gio.Files` in `files` and/or a list of `uris` and/or list of
    `paths`. This lists are combined together.

    if `track`, it is a user-level application.
    if `activate`, activate rather than start a new version.

    `app_rec` is either an `GAppInfo` or (`GAppInfo`, desktop_file_path) tuple.

    `work_dir`: overwrite work directory of application.

    Raises `SpawnError` on failed program start.
    """
    assert app_info
    assert not (bool(paths) and bool(uris)), (
        "either paths or uris must be given: " + repr((paths, uris))
    )

    svc = get_applications_matcher_service()
    app_id = application_id(app_info, desktop_file)

    if activate and app_id and svc.application_is_running(app_id):
        svc.application_to_front(app_id)
        return True

    launch_callback = None
    if track:
        # An launch callback closure for the @app_id
        def app_launch_callback(argv, pid, _notify_id, _files, _timestamp):
            if not settings.is_known_terminal_executable(argv[0]):
                svc.launched_application(app_id, pid)

        launch_callback = app_launch_callback

    files = list(files)
    if paths:
        files.extend(map(Gio.File.new_for_path, paths))

    if uris:
        files.extend(map(Gio.File.new_for_uri, uris))

    desktop_launch.launch_app_info(
        app_info,
        files,
        timestamp=uievents.current_event_time(),
        desktop_file=desktop_file,
        launch_cb=launch_callback,
        screen=screen,
        work_dir=work_dir,
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
        self.register: dict[str, str] = {}
        self._get_wnck_screen_windows_stacked()
        scheduler.get_scheduler().connect("finish", self._on_finish)
        self._load()

    @classmethod
    def _get_wnck_screen_windows_stacked(cls) -> ty.Iterable["Wnck.Window"]:
        if Wnck and (screen := Wnck.Screen.get_default()):
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

    def _on_finish(self, _sched: ty.Any) -> None:
        self._pickle_register(self.register, self._get_filename())

    def _unpickle_register(self, pickle_file: str) -> dict[str, str] | None:
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
        if not application:
            self.output_debug("no application for window", window)
            return False

        cgr = window.get_class_group()
        if not cgr:
            self.output_debug("no regclass for window", window)
            return False

        res_class = cgr.get_res_class()
        if not res_class:
            self.output_debug("no res_class for window", window)
            return False

        if self.register.get(app_id) in (application.get_name(), res_class):
            return True

        return app_id in (application.get_name().lower(), res_class.lower())

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
        if not app_id:
            return None

        return self.register.get(app_id)

    def application_is_running(self, app_id: str) -> bool:
        for win in self._get_wnck_screen_windows_stacked():
            if (
                win
                and win.get_application()
                and self._is_match(app_id, win)
                and win.get_window_type() == Wnck.WindowType.NORMAL
            ):
                self.output_debug("application is running", app_id)
                return True

        self.output_debug("application is NOT running", app_id)
        return False

    def _get_application_windows(
        self, app_id: str
    ) -> ty.Iterator["Wnck.Window"]:
        if not Wnck:
            return

        for win in self._get_wnck_screen_windows_stacked():
            if (
                win
                and win.get_application()
                and self._is_match(app_id, win)
                and win.get_window_type() == Wnck.WindowType.NORMAL
            ):
                yield win

    def application_to_front(self, app_id: str) -> None:
        application_windows = list(self._get_application_windows(app_id))
        self.output_debug(
            "application_to_front", "windows", application_windows
        )
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
        cur_screen = application_windows[0].get_screen()
        if not cur_screen:
            self.output_debug(
                "_to_front_application_style no cur_screen for application"
            )
            return

        cur_workspace = cur_screen.get_active_workspace()
        if not cur_workspace:
            self.output_debug(
                "_to_front_application_style no cur_workspace for application"
            )
            return

        # get all visible windows in stacking order on current workspace
        vis_windows = [
            win
            for win in self._get_wnck_screen_windows_stacked()
            if (
                win
                and win.get_window_type() == Wnck.WindowType.NORMAL
                and win.is_visible_on_workspace(cur_workspace)
            )
        ]

        self.output_debug(
            "_to_front_application_style vis_windows", vis_windows
        )

        # sort windows into "bins" by workspace
        workspaces: dict[Wnck.Workspace, list[Wnck.Window]] = defaultdict(list)
        for win in application_windows:
            if (
                win
                and win.get_window_type() == Wnck.WindowType.NORMAL
                and (wspc := win.get_workspace())
            ):
                workspaces[wspc].append(win)

        cur_wspc_windows = workspaces[cur_workspace]
        focus_windows = []

        # check if the application's window on current workspace are the topmost
        if (
            cur_wspc_windows
            and vis_windows
            and set(vis_windows[-len(cur_wspc_windows) :])
            != set(cur_wspc_windows)
        ):
            focus_windows = cur_wspc_windows
            # if the topmost window is already active, take another
            if focus_windows[-1] == vis_windows[-1]:
                focus_windows.pop()

        else:
            # all windows are focused, find on next workspace
            all_workspaces = cur_screen.get_workspaces()
            all_workspaces.pop(cur_workspace.get_number())

            for wspc in all_workspaces:
                focus_windows = workspaces[wspc]
                if focus_windows:
                    break

            else:
                # no windows on other workspaces, so we rotate among the
                # local ones
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
        self.output_debug("_focus_windows", "windows", windows)
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
                self.output_debug("_focus_windows", "activate", window, wspc)
                wspc.activate(evttime)

            self.output_debug("_focus_windows", "activate_transient", window)
            window.activate_transient(evttime)

        self.output_debug("_focus_windows", "all focused")

    def application_close_all(self, app_id: str) -> None:
        application_windows = self._get_application_windows(app_id)
        evttime = uievents.current_event_time()
        for win in application_windows:
            if not win.is_skip_tasklist():
                win.close(evttime)


# Get the (singleton) ApplicationsMatcherService"
get_applications_matcher_service = ApplicationsMatcherService.instance


def _split_string(inp: bytes, length: int) -> ty.Iterator[bytes]:
    """Split @inp in pieces of @length

    >>> list(_split_string(b"abcdefghijk", 3))
    [b"abc", b"def", b"ghi", b"jk"]

    """
    while inp:
        yield inp[:length]
        inp = inp[length:]


class AsyncCommand(pretty.OutputMixin):
    """Run a command asynchronously (using the GLib mainloop).

    call @finish_callback when command terminates, or
    when command is killed after @timeout_s seconds, whichever
    comes first.

    If @timeout_s is None, no timeout is used

    If stdin is a byte string, it is supplied on the command's stdin.

    If env is None, command will inherit the parent's environment.

    finish_callback -> (AsyncCommand, stdout_output, stderr_output)

    Attributes:
    self.exit_status  Set after process exited
    self.finished     bool
    """

    # the maximum input (bytes) we'll read in one shot (one io_callback)
    max_input_buf = 512 * 1024

    def __init__(
        self,
        argv: list[str],
        finish_callback: ty.Callable[[AsyncCommand, bytes, bytes], None],
        timeout_s: int | None,
        stdin: bytes | None = None,
        env: ty.Any = None,
    ) -> None:
        self.stdout: list[bytes] = []
        self.stderr: list[bytes] = []
        self.stdin: list[bytes] = []
        self.timeout = False
        self.killed = False
        self.finished = False
        self.finish_callback = finish_callback
        self.exit_status: int | None = None

        self.output_debug("AsyncCommand:", argv)

        flags = GLib.SPAWN_SEARCH_PATH | GLib.SPAWN_DO_NOT_REAP_CHILD
        kwargs = {}
        if env is not None:
            kwargs["envp"] = env

        pid, stdin_fd, stdout_fd, stderr_fd = GLib.spawn_async(
            argv,
            standard_output=True,
            standard_input=True,
            standard_error=True,
            flags=flags,
            **kwargs,
        )

        if stdin:
            self.stdin = list(_split_string(stdin, self.max_input_buf))
            in_io_flags = (
                GLib.IO_OUT | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL
            )
            GLib.io_add_watch(
                stdin_fd, in_io_flags, self._in_io_callback, self.stdin
            )
        else:
            os.close(stdin_fd)

        io_flags = GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL
        GLib.io_add_watch(stdout_fd, io_flags, self._io_callback, self.stdout)
        GLib.io_add_watch(stderr_fd, io_flags, self._io_callback, self.stderr)
        self.pid = pid
        GLib.child_watch_add(pid, self._child_callback)
        if timeout_s is not None:
            GLib.timeout_add_seconds(timeout_s, self._timeout_callback)

    def _io_callback(
        self, sourcefd: int, condition: int, databuf: list[bytes]
    ) -> bool:
        if condition & GLib.IO_IN:
            databuf.append(os.read(sourcefd, self.max_input_buf))
            return True

        return False

    def _in_io_callback(
        self, sourcefd: int, condition: int, databuf: list[bytes]
    ) -> bool:
        """write to child's stdin"""
        if condition & GLib.IO_OUT:
            if not databuf:
                os.close(sourcefd)
                return False

            data = databuf.pop(0)
            written = os.write(sourcefd, data)
            if written < len(data):
                databuf.insert(0, data[written:])

            return True

        return False

    def _child_callback(self, pid: int, condition: int) -> None:
        # @condition is the &status field of waitpid(2) (C library)
        self.exit_status = os.WEXITSTATUS(condition)
        self.finished = True
        self.finish_callback(
            self, b"".join(self.stdout), b"".join(self.stderr)
        )

    def _timeout_callback(self) -> None:
        "send term signal on timeout"
        if not self.finished:
            self.timeout = True
            os.kill(self.pid, signal.SIGTERM)
            GLib.timeout_add_seconds(2, self._kill_callback)

    def _kill_callback(self) -> None:
        "Last resort, send kill signal"
        if not self.finished:
            self.killed = True
            os.kill(self.pid, signal.SIGKILL)


def spawn_terminal(
    workdir: str | None = None, screen: str | None = None
) -> bool:
    "Raises SpawnError"
    term = settings.get_configured_terminal()
    if not term:
        return False

    notify = term["startup_notify"]
    app_id = term["desktopid"]
    argv = term["argv"]
    return desktop_launch.spawn_app_id(app_id, argv, workdir, notify, screen)


def spawn_in_terminal(argv: list[str], workdir: str | None = None) -> bool:
    "Raises SpawnError"
    term = settings.get_configured_terminal()
    if not term:
        return False

    notify = term["startup_notify"]
    _argv = list(term["argv"])
    if term["exearg"]:
        _argv.append(term["exearg"])

    _argv.extend(argv)
    return desktop_launch.spawn_app_id(
        term["desktopid"], _argv, workdir, notify
    )


def spawn_async_notify_as(app_id: str, argv: list[str]) -> bool:
    """
    Spawn argument list @argv and startup-notify as
    if application @app_id is starting (if possible)

    raises SpawnError
    """
    return desktop_launch.spawn_app_id(app_id, argv, None, True)


def spawn_async(
    argv: ty.Collection[str],
    in_dir: str = ".",
    *,
    finish_callback: ty.Callable[[int], None] | None = None,
) -> bool:
    """
    Silently spawn @argv in the background

    Returns False on failure
    """
    try:
        return spawn_async_raise(argv, in_dir, finish_callback=finish_callback)
    except SpawnError as exc:
        pretty.print_debug(__name__, "spawn_async", argv, exc)
        return False


def spawn_async_raise(
    argv: ty.Collection[str],
    workdir: str = ".",
    *,
    finish_callback: ty.Callable[[int], None] | None = None,
) -> bool:
    """
    A version of spawn_async that raises on error.

    raises SpawnError
    """
    pretty.print_debug(__name__, "spawn_async", argv, workdir)
    try:
        res = GLib.spawn_async(
            argv, working_directory=workdir, flags=GLib.SPAWN_SEARCH_PATH
        )
        if finish_callback and res:

            def _callback(pid: int, condition: int) -> None:
                finish_callback(os.WEXITSTATUS(condition))

            GLib.child_watch_add(res[0], _callback)

        return bool(res)
    except GLib.GError as exc:
        raise SpawnError(exc.message) from exc  # pylint: disable=no-member

    return False


def _try_register_pr_pdeathsig() -> None:
    """
    Register pr_set_pdeathsig (linux-only) for the calling process
    which is a signal delivered when its parent dies.

    This should ensure child processes die with the parent.
    """
    pr_set_pdeathsig = 1
    sighup = 1
    if sys.platform != "linux2":
        return

    with suppress(ImportError):
        # pylint: disable=import-outside-toplevel
        import ctypes

    with suppress(AttributeError, OSError):
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(pr_set_pdeathsig, sighup)


def _on_child_exit(
    pid: int, condition: int, user_data: tuple[ty.Any, bool]
) -> None:
    # @condition is the &status field of waitpid(2) (C library)
    argv, respawn = user_data
    if respawn:
        is_signal = os.WIFSIGNALED(condition)
        if is_signal and respawn:

            def callback(*args):
                _spawn_child(*args)
                return False

            GLib.timeout_add_seconds(10, callback, argv, respawn)


def _spawn_child(
    argv: list[str], respawn: bool = True, display: str | None = None
) -> int:
    """
    Spawn argv in the mainloop and keeping it as a child process
    (it will be made sure to exit with the parent).

    @respawn: If True, respawn if child dies abnormally

    raises launch.SpawnError
    returns pid
    """
    flags = GLib.SPAWN_SEARCH_PATH | GLib.SPAWN_DO_NOT_REAP_CHILD
    envp: list[str] = []
    if display:
        # environment is passed as a sequence of strings
        envd = os.environ.copy()
        envd["DISPLAY"] = display
        envp = ["=".join((k, v)) for k, v in envd.items()]

    try:
        pid: int
        pid, *_fds = GLib.spawn_async(
            argv,
            envp,
            flags=flags,
            child_setup=_try_register_pr_pdeathsig,
        )
    except GLib.GError as exc:
        raise SpawnError(str(exc)) from exc

    if pid:
        GLib.child_watch_add(pid, _on_child_exit, (argv, respawn))

    return pid


def start_plugin_helper(
    name: str, respawn: bool, display: str | None = None
) -> int:
    """
    @respawn: If True, respawn if child dies abnormally

    raises SpawnError

    UNUSED
    """
    argv = [sys.executable]
    argv.extend(sys.argv)
    argv.append(f"--exec-helper={name}")
    pretty.print_debug(__name__, "Spawning", argv)
    return _spawn_child(argv, respawn, display=display)


def show_path(path: str) -> None:
    """Open local @path with default viewer"""
    # Implemented using Gtk.show_uri
    gfile = Gio.File.new_for_path(path)
    if not gfile:
        return

    url = gfile.get_uri()
    show_url(url)


def show_url(url: str) -> bool:
    """Open any @url with default viewer"""

    # if there is no schema w url add default http://
    # this allow open urls like 'www.foobar.com'.
    url = url.strip()

    purl = urllib.parse.urlparse(url)
    if not purl.scheme:
        url = f"http://{url}"

    try:
        pretty.print_debug(__name__, "show_url", url)
        return ty.cast(
            "bool",
            Gtk.show_uri(
                Gdk.Screen.get_default(), url, Gtk.get_current_event_time()
            ),
        )
    except GLib.GError as exc:
        pretty.print_error(__name__, "Gtk.show_uri:", exc)

    return False


def show_help_url(url: str) -> bool:
    """Try at length to display a startup notification for the help browser.

    Return False if there is no handler for the help URL
    """
    ## Check that the system help viewer is Yelp,
    ## and if it is, launch its startup notification.
    scheme = Gio.File.new_for_uri(url).get_uri_scheme()
    default = Gio.app_info_get_default_for_uri_scheme(scheme)
    if not default:
        return False

    help_viewer_id = None

    for hv in ("yelp.desktop", "org.gnome.Yelp.desktop"):
        try:
            yelp = Gio.DesktopAppInfo.new(hv)
        except (TypeError, RuntimeError):
            pass
        else:
            help_viewer_id = hv
            break

    if not help_viewer_id:
        return show_url(url)

    cmd_path = fileutils.lookup_exec_path(default.get_executable())
    yelp_path = fileutils.lookup_exec_path(yelp.get_executable())
    if cmd_path and yelp_path and os.path.samefile(cmd_path, yelp_path):
        with suppress(SpawnError):
            spawn_async_notify_as(help_viewer_id, [cmd_path, url])
            return True

    return show_url(url)


def get_display_path_for_bytestring(filepath: str | bytes) -> str:
    """Return a unicode path for display for string or bytestring @filepath

    Will use glib's filename decoding functions, and will
    format nicely (denote home by ~/ etc)
    """
    desc: str = GLib.filename_display_name(filepath)
    homedir = system.get_homedir()
    if desc.startswith(homedir) and homedir != desc:
        desc = f"~{desc[len(homedir) :]}"

    return desc


if __name__ == "__main__":
    import doctest

    doctest.testmod()
