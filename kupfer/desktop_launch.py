from __future__ import annotations

import os
import typing as ty
from contextlib import suppress
from pathlib import Path
from dataclasses import dataclass

import xdg.DesktopEntry
import xdg.Exceptions
from gi.repository import Gdk, Gio, GLib, Gtk

from kupfer import terminal
from kupfer.support import desktop_parse, kupferstring, pretty

__all__ = ["launch_app_info", "spawn_app", "spawn_app_id"]

STARTUP_ENV = "DESKTOP_STARTUP_ID"

# TODO: Broadcast Gio's launched message on dbus
# NOTE: GDK's startup notification things that we use
#       are really only sending xmessages. (roughly).


def debug_log(*args: ty.Any) -> None:
    pretty.print_debug(__name__, *args)


warning_log = debug_log


def error_log(*args: ty.Any) -> None:
    pretty.print_error(__name__, *args)


def exc_log() -> None:
    pretty.print_exc(__name__)


class SpawnError(Exception):
    "Error starting application"


class ResourceLookupError(Exception):
    "Unable to find resource"


class ResourceReadError(Exception):
    "Unable to open resource"


def _find_desktop_file(desk_id: str) -> str:
    """Find file for @desk_id or raise ResourceLookupError

    Desktop files are found by appending /applications/ to
    $XDG_DATA_DIRS, but if they are located in subdirs of that,
    then additional 'subdirectory-' prefixes are used.
    """
    if not desk_id:
        raise ResourceLookupError("Empty id")

    try:
        return next(xdg.BaseDirectory.load_data_paths("applications", desk_id))  # type: ignore
    except StopIteration:
        ## it was not found as an immediate child of the data paths,
        ## so we split by the hyphens and search deeper
        file_id = desk_id
        directories = ["applications"]

        def lookup(path: list[str]) -> str | None:
            """Return location for @path if exists, else none"""
            return next(xdg.BaseDirectory.load_data_paths(*path), None)

        def get_dir_id_depth(desk_id: str, depth: int) -> tuple[str, str]:
            "split 'hyph-example-id' at the nth hyphen"
            parts = desk_id.split("-", depth)
            return "-".join(parts[:depth]), "-".join(parts[depth:])

        while True:
            ## try the first parts of the id to see if it matches a directory
            for x in range(1, 4):
                dirname, rest_id = get_dir_id_depth(file_id, x)
                if rest_id and lookup(directories + [dirname]):
                    file_id = rest_id
                    directories.append(dirname)
                    break
            else:
                ## we did not reach break
                break

            if desktop_file_path := lookup(directories + [file_id]):
                return desktop_file_path

    raise ResourceLookupError(f"Cannot locate '{desk_id}'")


def _read_desktop_info(desktop_file: str) -> dict[str, str | bool]:
    """
    Get the keys StartupNotify, Terminal, Exec, Path, Icon
    Return dict with bool and unicode values
    """
    # Return values in unicode
    try:
        entry = xdg.DesktopEntry.DesktopEntry(desktop_file)
    except xdg.Exceptions.Error as exc:
        raise ResourceReadError from exc

    if not entry.getExec():
        raise ResourceReadError("Invalid data: empty Exec key")

    return {
        "Terminal": entry.getTerminal(),
        "StartupNotify": entry.getStartupNotify(),
        "Exec": entry.getExec(),
        "Path": entry.getPath(),
        "Icon": entry.getIcon(),
        "Name": entry.getName(),
    }


def app_to_desktop_info(app_info: Gio.AppInfo) -> dict[str, str | bool]:
    return {
        "Exec": app_info.get_commandline() or "",
        "Name": app_info.get_name(),
        "Icon": "",
        "Path": "",
        "Terminal": False,
        "StartupNotify": False,
    }


def _two_part_unescaper(
    instr: str, repfunc: ty.Callable[[str], str | None]
) -> str:
    """
    Handle embedded format codes

    Scan @s two characters at a time and replace using @repfunc

    TODO: similar function in desktop_parse; merge?
    """
    if not instr:
        return instr

    def _inner():
        sit = zip(instr, instr[1:])
        for cur, nex in sit:
            key = cur + nex
            if (rep := repfunc(key)) is not None:
                yield rep
                # skip a step in the iter
                try:
                    next(sit)
                except StopIteration:
                    return

            else:
                yield cur

        yield instr[-1]

    return "".join(_inner())


def _get_file_path(gfile: Gio.File) -> str:
    return (gfile.get_path() or gfile.get_uri()) if gfile else ""  # type: ignore


@dataclass
class _Flags:
    did_see_small_f: bool = False
    did_see_large_f: bool = False


def _replace_format_specs(
    argv: list[str],
    location: str,
    desktop_info: dict[str, ty.Any],
    gfilelist: list[Gio.File],
) -> tuple[bool, bool, list[str]]:
    """
    http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html

    Replace format specifiers

    %% literal %
    %f file
    %F list of files
    %u URL
    %U list of URLs
    %i --icon <Icon key>
    %c Translated name
    %k location of .desktop file

    deprecated are removed:
    %d %D %n %N %v %m

    apart from those, all other.. stay and are ignored
    Like other implementations, we do actually insert
    a local path for %u and %U if it exists.

    Return (supports_single, added_at_end, argv)

    supports_single: Launcher only supports a single file
                     caller has to re-call for each file
    added_at_end:    No format found for the file, it was added
                     at the end
    """
    supports_single_file = False
    files_added_at_end = False

    flags = _Flags()

    fileiter = iter(gfilelist)

    def get_next_file_path() -> str:
        with suppress(StopIteration):
            file = next(fileiter)
            return _get_file_path(file)

        return ""

    # pylint: disable=too-many-return-statements
    def replace_single_code(key: str) -> str | None:
        "Handle all embedded format codes, including those to be removed"
        if key in ("%d", "%D", "%n", "%N", "%v", "%m"):  # deprecated keys
            return ""

        if key == "%%":
            return "%"

        if key in ("%f", "%u"):
            if flags.did_see_large_f or flags.did_see_small_f:
                warning_log("Warning, multiple file format specs!")
                return ""

            flags.did_see_small_f = True
            return get_next_file_path()

        if key == "%c":
            return desktop_info["Name"] or location

        if key == "%k":
            return location

        return None

    def replace_array_format(elem: str) -> tuple[bool, str | list[str]]:
        """
        Handle array format codes -- only recognized as single arguments

        Return  flag, arglist
        where flag is true if something was replaced
        """
        if elem in ("%U", "%F"):
            if flags.did_see_large_f or flags.did_see_small_f:
                warning_log("Warning, multiple file format specs!")
                return True, []

            flags.did_see_large_f = True
            return True, list(filter(bool, map(_get_file_path, gfilelist)))

        if elem == "%i":
            if desktop_info["Icon"]:
                return True, ["--icon", desktop_info["Icon"]]

            return True, []

        return False, elem

    new_argv: list[str] = []
    for x in argv:
        if not x:
            # the arg is an empty string, we don't need extra processing
            new_argv.append(x)
            continue

        succ, newargs = replace_array_format(x)
        if succ:
            new_argv.extend(newargs)
        else:
            if arg := _two_part_unescaper(x, replace_single_code):
                new_argv.append(arg)

    if len(gfilelist) > 1 and not flags.did_see_large_f:
        supports_single_file = True

    if not flags.did_see_small_f and not flags.did_see_large_f and gfilelist:
        files_added_at_end = True
        new_argv.append(get_next_file_path())

    return supports_single_file, files_added_at_end, new_argv


def _file_for_app_info(app_info: Gio.AppInfo) -> str | None:
    try:
        return _find_desktop_file(app_info.get_id())
    except ResourceLookupError:
        exc_log()

    return None


def _info_for_desktop_file(
    desktop_file: str | None,
) -> dict[str, ty.Any] | None:
    if desktop_file:
        try:
            return _read_desktop_info(desktop_file)
        except ResourceReadError:
            exc_log()

    return None


LaunchCallback = ty.Callable[[list[str], int, int, list[str], int], None]


# pylint: disable=too-many-locals
def launch_app_info(
    app_info: Gio.AppInfo,
    gfiles: ty.Iterable[Gio.File] | None = None,
    in_terminal: bool | None = None,
    timestamp: float | None = None,
    desktop_file: str | None = None,
    launch_cb: LaunchCallback | None = None,
    screen: Gdk.Screen | None = None,
) -> bool:
    """
    Launch @app_info, opening @gfiles

    @in_terminal: override Terminal flag
    @timestamp: override timestamp
    @desktop_file: specify location of desktop file
    @launch_cb: Called once per launched process, like ``spawn_app``

    Will pass on exceptions from spawn_app
    """
    gfiles = list(gfiles or [])
    desktop_file = desktop_file or _file_for_app_info(app_info)
    desktop_info = _info_for_desktop_file(desktop_file)
    if not desktop_file or not desktop_info:
        # Allow in-memory app_info creations (without id or desktop file)
        desktop_file = ""
        desktop_info = app_to_desktop_info(app_info)
        # in this case, the command line is already primarily escaped
        argv = desktop_parse.parse_argv(desktop_info["Exec"])  # type: ignore
    else:
        # In the normal case, we must first escape one round
        argv = desktop_parse.parse_unesc_argv(desktop_info["Exec"])

    assert argv and argv[0]

    # Now Resolve the %f etc format codes
    multiple_needed, _missing_format, launch_argv = _replace_format_specs(
        argv, desktop_file, desktop_info, gfiles
    )

    if not multiple_needed:
        # Launch 1 process
        launch_records = [(launch_argv, gfiles)]
    else:
        # Launch one process per file
        launch_records = [(launch_argv, [gfiles[0]])]
        for file in gfiles[1:]:
            _ignore1, _ignore2, launch_argv = _replace_format_specs(
                argv, desktop_file, desktop_info, [file]
            )
            launch_records.append((launch_argv, [file]))

    notify = bool(desktop_info["StartupNotify"])
    workdir = desktop_info["Path"] or None

    if in_terminal is None:
        in_terminal = desktop_info["Terminal"]  # type: ignore

    if in_terminal:
        term = terminal.get_configured_terminal()
        notify = notify or bool(term["startup_notify"])

    for argv, files in launch_records:
        if in_terminal:
            term = terminal.get_configured_terminal()
            targv = list(term["argv"])
            if exearg := term["exearg"]:
                targv.append(exearg)

            argv = targv + argv

        if not spawn_app(
            app_info,
            argv,
            files,
            workdir,  # type: ignore
            notify,
            timestamp=timestamp,
            launch_cb=launch_cb,
            screen=screen,
        ):
            return False

    return True


def spawn_app_id(
    app_id: str,
    argv: list[str],
    workdir: str | None = None,
    startup_notify: bool = True,
    screen: Gdk.Screen | None = None,
) -> bool:
    """
    Spawn @argv trying to notify it as if it is app_id
    """
    try:
        app_info = _get_info_for_id(app_id)
    except (TypeError, RuntimeError):
        app_info = None
        startup_notify = False

    return bool(
        spawn_app(app_info, argv, [], workdir, startup_notify, screen=screen)
    )


def spawn_app(
    app_info: Gio.AppInfo | None,
    argv: list[str],
    filelist: list[ty.Any],
    workdir: str | None = None,
    startup_notify: bool = True,
    timestamp: float | None = None,
    launch_cb: LaunchCallback | None = None,
    screen: Gdk.Screen | None = None,
) -> int:
    """
    Spawn app.

    @argv: argument list including files
    @workdir: where to set workdir if not cwd
    @app_info: Used for startup notification, if @startup_notify is True
    @filelist: Used for startup notification
    @startup_notify: Use startup notification
    @timestamp: Event timestamp
    @launch_cb: Called if successful with
                (argv, pid, notify_id, filelist, timestamp)
    @screen: GdkScreen on which to put the application

    return pid if successful
    raise SpawnError on error

    TODO: use screen parameter
    """
    notify_id = None
    if startup_notify:
        display = Gdk.Display.get_default()
        ctx = display.get_app_launch_context()
        ctx.set_timestamp(timestamp or Gtk.get_current_event_time())
        if screen:
            ctx.set_screen(screen)
        # This not only returns the string ID but
        # it actually starts the startup notification!
        notify_id = ctx.get_startup_notify_id(app_info, filelist)
        child_env_add = {STARTUP_ENV: notify_id}
    else:
        child_env_add = {}

    if not workdir or not Path(workdir).exists():
        workdir = "."

    argv_ = list(_locale_encode_argv(argv))

    try:
        pid, *_ig = GLib.spawn_async(
            argv_,
            flags=GLib.SpawnFlags.SEARCH_PATH,
            working_directory=workdir,
            child_setup=child_setup,
            user_data=child_env_add,
        )
        debug_log("Launched", argv_, notify_id, "pid:", pid)

    except GLib.GError as exc:
        error_log("Error Launching ", argv_, str(exc))
        if notify_id:
            Gdk.notify_startup_complete_with_id(notify_id)

        raise SpawnError(exc.message) from exc  # pylint: disable=no-member

    if launch_cb:
        launch_cb(argv, pid, notify_id, filelist, timestamp)  # type: ignore

    return pid  # type: ignore


def child_setup(add_environ: dict[str, str]) -> None:
    """Called to setup the child process before exec()
    @add_environ is a dict for extra env variables
    """
    for key, val in add_environ.items():
        if val is None:
            val = ""

        os.putenv(key, val)


def _locale_encode_argv(argv: list[ty.AnyStr]) -> ty.Iterator[str]:
    for x in argv:
        if isinstance(x, str):
            yield kupferstring.tolocale(x).decode("UTF-8", "replace")
        else:
            yield x.decode("UTF-8", "replace")


def _get_info_for_id(app_id: str) -> Gio.DesktopAppInfo:
    return Gio.DesktopAppInfo.new(app_id)


if __name__ == "__main__":
    while True:
        id_ = input("Give me an App ID > ")
        launch_app_info(_get_info_for_id(id_ + ".desktop"), [])
        # launch_app_info(Gio.AppInfo("gvim"), [Gio.File(".")])
