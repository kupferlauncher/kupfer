from __future__ import annotations

import functools
import itertools
import locale
import os
import signal
import sys
import tempfile
import typing as ty
from contextlib import suppress
from os import path as os_path
from pathlib import Path

from gi.repository import Gdk, Gio, GLib, Gtk

from kupfer import desktop_launch, launch, terminal
from kupfer.desktop_launch import SpawnError
from kupfer.support import desktop_parse, kupferstring, pretty

FilterFunc = ty.Callable[[str], bool]


def get_dirlist(
    folder: str,
    max_depth: int = 0,
    include: ty.Optional[FilterFunc] = None,
    exclude: ty.Optional[FilterFunc] = None,
) -> ty.Iterator[str]:
    """
    Return a list of absolute paths in folder
    include, exclude: a function returning a boolean
    def include(filename):
        return ShouldInclude

    """

    def include_file(file):
        return (not include or include(file)) and (
            not exclude or not exclude(file)
        )

    for dirname, dirnames, fnames in os.walk(folder):
        # skip deep directories
        depth = len(os.path.relpath(dirname, folder).split(os.path.sep)) - 1
        if depth >= max_depth:
            dirnames.clear()
            continue

        excl_dir = []
        for directory in dirnames:
            if include_file(directory):
                yield os_path.join(dirname, directory)
            else:
                excl_dir.append(directory)

        yield from (
            os_path.join(dirname, file) for file in fnames if include_file(file)
        )

        for directory in reversed(excl_dir):
            dirnames.remove(directory)


_SortItem = ty.TypeVar("_SortItem")


def locale_sort(
    seq: ty.Iterable[_SortItem], key: ty.Callable[[_SortItem], ty.Any] = str
) -> ty.List[_SortItem]:
    """Return @seq of objects with @key function as a list sorted
    in locale lexical order

    >>> locale.setlocale(locale.LC_ALL, "C")
    'C'
    >>> locale_sort("abcABC")
    ['A', 'B', 'C', 'a', 'b', 'c']

    >>> locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    'en_US.UTF-8'
    >>> locale_sort("abcABC")
    ['a', 'A', 'b', 'B', 'c', 'C']
    """

    def locale_cmp(val1, val2):
        return locale.strcoll(key(val1), key(val2))

    seq = seq if isinstance(seq, list) else list(seq)
    seq.sort(key=functools.cmp_to_key(locale_cmp))
    return seq


def _argv_to_locale(argv: list[str]) -> list[bytes]:
    "encode unicode strings in @argv according to the locale encoding"
    return [kupferstring.tolocale(A) if isinstance(A, str) else A for A in argv]


def _split_string(inp: bytes, length: int) -> ty.Iterator[bytes]:
    """Split @inp in pieces of @length

    >>> list(_split_string(b"abcdefghijk", 3))
    [b"abc", b"def", b"ghi", b"jk"]

    """
    while inp:
        yield inp[:length]
        inp = inp[length:]


class AsyncCommand(pretty.OutputMixin):
    """
    Run a command asynchronously (using the GLib mainloop)

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
        stdin: ty.Optional[bytes] = None,
        env: ty.Any = None,
    ) -> None:
        self.stdout: list[bytes] = []
        self.stderr: list[bytes] = []
        self.stdin: list[bytes] = []
        self.timeout = False
        self.killed = False
        self.finished = False
        self.finish_callback = finish_callback
        self.exit_status: ty.Optional[int] = None

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
            in_io_flags = GLib.IO_OUT | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL
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
        self.finish_callback(self, b"".join(self.stdout), b"".join(self.stderr))

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
    workdir: ty.Optional[str] = None, screen: ty.Optional[str] = None
) -> bool:
    "Raises SpawnError"
    term = terminal.get_configured_terminal()
    notify = term["startup_notify"]
    app_id = term["desktopid"]
    argv = term["argv"]
    return desktop_launch.spawn_app_id(app_id, argv, workdir, notify, screen)


def spawn_in_terminal(
    argv: list[str], workdir: ty.Optional[str] = None
) -> bool:
    "Raises SpawnError"
    term = terminal.get_configured_terminal()
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


def spawn_async(argv: ty.Collection[str], in_dir: str = ".") -> bool:
    """
    Silently spawn @argv in the background

    Returns False on failure
    """
    try:
        return spawn_async_raise(argv, in_dir)
    except SpawnError as exc:
        pretty.print_debug(__name__, "spawn_async", argv, exc)
        return False


def spawn_async_raise(argv: ty.Collection[str], workdir: str = ".") -> bool:
    """
    A version of spawn_async that raises on error.

    raises SpawnError
    """
    # FIXME: How to support locale strings?
    # argv = _argv_to_locale(argv)
    pretty.print_debug(__name__, "spawn_async", argv, workdir)
    try:
        res = GLib.spawn_async(
            argv, working_directory=workdir, flags=GLib.SPAWN_SEARCH_PATH
        )
        return bool(res)
    except GLib.GError as exc:
        raise SpawnError(exc.message) from exc  # pylint: disable=no-member

    return False


def argv_for_commandline(cli: str) -> list[str]:
    return desktop_parse.parse_argv(cli)


def launch_commandline(
    cli: str, name: ty.Optional[str] = None, in_terminal: bool = False
) -> bool:
    "Raises SpawnError"
    argv = desktop_parse.parse_argv(cli)
    pretty.print_error(__name__, "Launch commandline is deprecated ")
    pretty.print_debug(
        __name__,
        "Launch commandline (in_terminal=",
        in_terminal,
        "):",
        argv,
        sep="",
    )

    if in_terminal:
        return spawn_in_terminal(argv)

    return spawn_async(argv)


def launch_app(
    app_info: Gio.AppInfo,
    files: ty.Iterable[str] = (),
    uris: ty.Iterable[str] = (),
    paths: ty.Iterable[str] = (),
) -> bool:
    "Raises SpawnError"

    # With files we should use activate=False
    return launch.launch_application(
        app_info, files, uris, paths, activate=False
    )


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
    try:
        pretty.print_debug(__name__, "show_url", url)
        return Gtk.show_uri(  # type: ignore
            Gdk.Screen.get_default(), url, Gtk.get_current_event_time()
        )
    except GLib.GError as exc:
        pretty.print_error(__name__, "Gtk.show_uri:", exc)

    return False


def _on_child_exit(
    pid: int, condition: int, user_data: tuple[ty.Any, bool]
) -> None:
    # @condition is the &status field of waitpid(2) (C library)
    argv, respawn = user_data
    if respawn:
        is_signal = os.WIFSIGNALED(condition)
        if is_signal and respawn:

            def callback(*args):
                spawn_child(*args)
                return False

            GLib.timeout_add_seconds(10, callback, argv, respawn)


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


def spawn_child(
    argv: list[str], respawn: bool = True, display: ty.Optional[str] = None
) -> int:
    """
    Spawn argv in the mainloop and keeping it as a child process
    (it will be made sure to exit with the parent).

    @respawn: If True, respawn if child dies abnormally

    raises utils.SpawnError
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

    return pid  # type: ignore


def start_plugin_helper(
    name: str, respawn: bool, display: ty.Optional[str] = None
) -> int:
    """
    @respawn: If True, respawn if child dies abnormally

    raises SpawnError
    """
    argv = [sys.executable]
    argv.extend(sys.argv)
    argv.append(f"--exec-helper={name}")
    pretty.print_debug(__name__, "Spawning", argv)
    return spawn_child(argv, respawn, display=display)


def show_help_url(url: str) -> bool:
    """
    Try at length to display a startup notification for the help browser.

    Return False if there is no handler for the help URL
    """
    ## Check that the system help viewer is Yelp,
    ## and if it is, launch its startup notification.
    scheme = Gio.File.new_for_uri(url).get_uri_scheme()
    default = Gio.app_info_get_default_for_uri_scheme(scheme)
    if not default:
        return False

    help_viewer_id = "yelp.desktop"

    try:
        yelp = Gio.DesktopAppInfo.new(help_viewer_id)
    except (TypeError, RuntimeError):
        return show_url(url)

    cmd_path = lookup_exec_path(default.get_executable())
    yelp_path = lookup_exec_path(yelp.get_executable())
    if cmd_path and yelp_path and os.path.samefile(cmd_path, yelp_path):
        with suppress(SpawnError):
            spawn_async_notify_as(help_viewer_id, [cmd_path, url])
            return True

    return show_url(url)


def lookup_exec_path(exename: str) -> ty.Optional[str]:
    "Return path for @exename in $PATH or None"
    env_path = os.environ.get("PATH") or os.defpath
    for execdir in env_path.split(os.pathsep):
        exepath = Path(execdir, exename)
        if os.access(exepath, os.R_OK | os.X_OK) and exepath.is_file():
            return str(exepath)

    return None


def is_directory_writable(dpath: str) -> bool:
    """If directory path @dpath is a valid destination to write new files?"""
    if not Path(dpath).is_dir():
        return False

    return os.access(dpath, os.R_OK | os.W_OK | os.X_OK)


def get_destpath_in_directory(
    directory: str, filename: str, extension: ty.Optional[str] = None
) -> str:
    """Find a good destpath for a file named @filename in path @directory
    Try naming the file as filename first, before trying numbered versions
    if the previous already exist.

    If @extension, it is used as the extension. Else the filename is split and
    the last extension is used
    """
    # find a nonexisting destname
    if extension:
        basename = filename + extension
        root, ext = filename, extension
    else:
        basename = filename
        root, ext = os_path.splitext(filename)

    ctr = itertools.count(1)
    destpath = Path(directory, basename)
    while destpath.exists():
        num = next(ctr)
        basename = f"{root}-{num}{ext}"
        destpath = Path(directory, basename)

    return str(destpath)


def get_destfile_in_directory(
    directory: str, filename: str, extension: ty.Optional[str] = None
) -> tuple[ty.Optional[ty.BinaryIO], ty.Optional[str]]:
    """Find a good destination for a file named @filename in path @directory.

    Like get_destpath_in_directory, but returns an open file object, opened
    atomically to avoid race conditions.

    Return (fileobj, filepath)
    """
    # retry if it fails
    for _retry in range(3):
        destpath = get_destpath_in_directory(directory, filename, extension)
        try:
            fileno = os.open(
                destpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666
            )
        except OSError as exc:
            pretty.print_error(__name__, exc)
        else:
            return (os.fdopen(fileno, "wb"), destpath)

    return (None, None)


def get_safe_tempfile() -> tuple[ty.BinaryIO, str]:
    """Return (fileobj, filepath) pointing to an open temporary file"""

    fileno, path = tempfile.mkstemp()
    return (os.fdopen(fileno, "wb"), path)


_homedir = os.path.expanduser("~/")
_homedir_len = len(_homedir)


def get_display_path_for_bytestring(filepath: ty.AnyStr) -> str:
    """Return a unicode path for display for bytestring @filepath

    Will use glib's filename decoding functions, and will
    format nicely (denote home by ~/ etc)
    """
    desc: str = GLib.filename_display_name(filepath)
    if desc.startswith(_homedir) and _homedir != desc:
        desc = f"~/{desc[_homedir_len:]}"

    return desc


def parse_time_interval(tstr: str) -> int:
    """
    Parse a time interval in @tstr, return whole number of seconds

    >>> parse_time_interval("2")
    2
    >>> parse_time_interval("1h 2m 5s")
    3725
    >>> parse_time_interval("2 min")
    120
    """
    weights = {
        "s": 1,
        "sec": 1,
        "m": 60,
        "min": 60,
        "h": 3600,
        "hours": 3600,
    }

    with suppress(ValueError):
        return int(tstr)

    total = 0
    amount = 0
    # Split the string in runs of digits and runs of characters
    for isdigit, group in itertools.groupby(tstr, lambda k: k.isdigit()):
        if not (part := "".join(group).strip()):
            continue

        if isdigit:
            amount = int(part)
        else:
            total += amount * weights.get(part.lower(), 0)
            amount = 0

    return total


if __name__ == "__main__":
    import doctest

    doctest.testmod()
