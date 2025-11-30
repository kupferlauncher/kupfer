import argparse
import gettext
import locale
import runpy
import sys
import typing as ty
from contextlib import suppress
from pathlib import Path

if ty.TYPE_CHECKING:
    from gettext import gettext as _

try:
    from kupfer import version_subst  # type:ignore
except ImportError:
    version_subst = None

__all__ = ("main",)


def _setup_locale_and_gettext() -> None:
    """Set up localization with gettext"""
    package_name = "kupfer"
    localedir = "./locale"
    for ldir in ("./locale", "/usr/local/share/locale/"):
        if Path(ldir).is_dir():
            localedir = ldir
            break

    if version_subst:
        package_name = version_subst.PACKAGE_NAME
        localedir = version_subst.LOCALEDIR

    # Install _() builtin for gettext; always returning unicode objects
    # also install ngettext()
    gettext.install(package_name, localedir=localedir, names=("ngettext",))
    # For Gtk.Builder, we need to call the C library gettext functions
    # As well as set the codeset to avoid locale-dependent translation
    # of the message catalog
    locale.bindtextdomain(package_name, localedir)
    locale.bind_textdomain_codeset(package_name, "UTF-8")
    # to load in current locale properly for sorting etc
    with suppress(locale.Error):
        locale.setlocale(locale.LC_ALL, "")


_setup_locale_and_gettext()


def _print(*args: ty.Any) -> None:
    enc = locale.getpreferredencoding(do_setlocale=False)
    sys.stdout.buffer.write(" ".join(args).encode(enc, "replace"))
    sys.stdout.buffer.write(b"\n")


def _make_help_text(
    program_options: list[tuple[str, str]], misc_options: list[tuple[str, str]]
) -> str:
    usage_string = _("Usage: kupfer [ OPTIONS | FILE ... ]")

    def format_options(opts):
        return "\n".join(f"  --{o:<15}  {h}" for o, h in opts)

    popts = format_options(program_options)
    mopts = format_options(misc_options)
    return f"{usage_string}\n\n{popts}\n\n{mopts}\n"


def _make_plugin_list() -> str:
    # require setup path and locales
    from kupfer.core import plugins  # pylint: disable=import-outside-toplevel

    plugin_header = _("Available plugins:")
    plugin_list = plugins.get_plugin_desc()
    return "\n".join((plugin_header, plugin_list))


def _get_options() -> argparse.Namespace:
    """Return a list of other application flags with --* prefix included."""

    from kupfer import version  # pylint: disable=import-outside-toplevel

    parser = argparse.ArgumentParser(
        prog=version.PROGRAM_NAME,
        description=version.SHORT_DESCRIPTION,
    )
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help=_("do not present main interface on launch"),
    )
    parser.add_argument(
        "--list-plugins", action="store_true", help=_("list available plugins")
    )
    parser.add_argument(
        "--debug", action="store_true", help=_("enable debug info")
    )
    # TRANS: --exec-helper=HELPER is an internal command
    # TRANS: that executes a helper program that is part of kupfer
    parser.add_argument("--exec-helper", nargs=1, help=_("run plugin helper"))
    parser.add_argument(
        "--no-colors",
        action="store_true",
        help=_("do not use colored text in terminal"),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{version.PACKAGE_NAME}  {version.VERSION}",
    )

    # Fix sys.argv that can be None in exceptional cases
    if sys.argv[0] is None:
        sys.argv[0] = "kupfer"

    args = parser.parse_args()

    if args.list_plugins:
        _print(_gtkmain(_make_plugin_list))
        raise SystemExit

    if args.exec_helper:
        _exec_helper(args.exec_helper[0])
        raise SystemExit(1)

    return args


def _print_banner() -> None:
    # require setup path and locales
    from kupfer import version  # pylint: disable=import-outside-toplevel

    if not sys.stdout or not sys.stdout.isatty():
        return

    banner = _(
        "%(PROGRAM_NAME)s: %(SHORT_DESCRIPTION)s\n"
        "   %(COPYRIGHT)s\n"
        "   %(WEBSITE)s\n"
    ) % vars(version)
    _print(banner)


def _set_process_title() -> None:
    try:
        import setproctitle  # pylint: disable=import-outside-toplevel
    except ImportError:
        pass
    else:
        setproctitle.setproctitle("kupfer")


def _exec_helper(helpername: str) -> None:
    runpy.run_module(helpername, run_name="__main__", alter_sys=True)
    raise SystemExit


def _gtkmain(
    run_function: ty.Callable[..., ty.Any],
    *args: ty.Any,
    **kwargs: ty.Any,
) -> ty.Any:
    import gi  # pylint: disable=import-outside-toplevel

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    with suppress(ValueError):
        gi.require_version("Wnck", "3.0")

    with suppress(ValueError):
        gi.require_version("AyatanaAppIndicator3", "0.1")

    return run_function(*args, **kwargs)


def _browser_start(quiet: bool) -> None:
    # pylint: disable=import-outside-toplevel
    from gi.repository import Gdk, GLib

    # program name; propagated to WM_NAME, WM_CLASS
    GLib.set_prgname("Kupfer")

    if not Gdk.Screen.get_default():  #pylint: disable=no-value-for-parameter
        print("No Screen Found, Exiting...", file=sys.stderr)
        sys.exit(1)

    from kupfer.ui import browser  # pylint: disable=import-outside-toplevel

    wctrl = browser.WindowController()
    wctrl.main(quiet=quiet)


def main() -> None:
    # parse commandline before importing UI
    cli_opts = _get_options()
    _print_banner()

    # pylint: disable=import-outside-toplevel
    from kupfer import version
    from kupfer.support import pretty

    if cli_opts.debug:
        pretty.DEBUG = True
        pretty.print_debug(
            __name__, "Version:", version.PACKAGE_NAME, version.VERSION
        )
        with suppress(ImportError):
            import debug

            debug.install()

    # enable colors only on terminal
    pretty.COLORS = sys.stdout.isatty() and not cli_opts.no_colors

    sys.excepthook = sys.__excepthook__
    _set_process_title()

    quiet = cli_opts.no_splash
    _gtkmain(_browser_start, quiet)
