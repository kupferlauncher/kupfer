import getopt
import gettext
import locale
import runpy
import sys
import typing as ty
from contextlib import suppress

try:
    from kupfer import version_subst  # type:ignore
except ImportError:
    version_subst = None

if ty.TYPE_CHECKING:
    _ = str


def _setup_locale_and_gettext() -> None:
    """Set up localization with gettext"""
    package_name = "kupfer"
    localedir = "./locale"
    if version_subst:
        package_name = version_subst.PACKAGE_NAME
        localedir = version_subst.LOCALEDIR
    # Install _() builtin for gettext; always returning unicode objects
    # also install ngettext()
    gettext.install(
        package_name, localedir=localedir, names=("ngettext",)  # unicode=True,
    )
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
    options_string = f"{usage_string}\n\n{popts}\n\n{mopts}\n"
    return options_string


def _make_plugin_list() -> str:
    # require setup path and locales
    from kupfer.core import plugins  # pylint: disable=import-outside-toplevel

    plugin_header = _("Available plugins:")
    plugin_list = plugins.get_plugin_desc()
    return "\n".join((plugin_header, plugin_list))


def get_options() -> list[str]:
    """Return a list of other application flags with --* prefix included."""

    program_options = [
        ("no-splash", _("do not present main interface on launch")),
        ("list-plugins", _("list available plugins")),
        ("debug", _("enable debug info")),
        # TRANS: --exec-helper=HELPER is an internal command
        # TRANS: that executes a helper program that is part of kupfer
        ("exec-helper=", _("run plugin helper")),
        ("no-colors", _("do not use colored text in terminal")),
    ]
    misc_options = [
        ("help", _("show usage help")),
        ("version", _("show version information")),
    ]

    # Fix sys.argv that can be None in exceptional cases
    if sys.argv[0] is None:
        sys.argv[0] = "kupfer"

    try:
        opts, _args = getopt.getopt(
            sys.argv[1:],
            "",
            [o for o, _h in program_options] + [o for o, _h in misc_options],
        )
    except getopt.GetoptError as exc:
        _print(str(exc))
        _print(_make_help_text(program_options, misc_options))
        raise SystemExit(1) from exc

    for key, val in opts:
        if key == "--list-plugins":
            _print(gtkmain(_make_plugin_list))
            raise SystemExit

        if key == "--help":
            _print(_make_help_text(program_options, misc_options))
            raise SystemExit

        if key == "--version":
            _print_version()
            raise SystemExit

        if key == "--relay":
            _print("WARNING: --relay is deprecated!")
            exec_helper("kupfer.keyrelay")
            raise SystemExit

        if key == "--exec-helper":
            exec_helper(val)
            raise SystemExit(1)

    # return list first of tuple pair
    return [tupl[0] for tupl in opts]


def _print_version() -> None:
    # require setup path and locales
    from kupfer import version  # pylint: disable=import-outside-toplevel

    _print(version.PACKAGE_NAME, version.VERSION)


def print_banner() -> None:
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


def exec_helper(helpername: str) -> None:
    runpy.run_module(helpername, run_name="__main__", alter_sys=True)
    raise SystemExit


def gtkmain(
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
        gi.require_version("AppIndicator3", "0.1")

    return run_function(*args, **kwargs)


def browser_start(quiet: bool) -> None:
    from gi.repository import Gdk  # pylint: disable=import-outside-toplevel

    if not Gdk.Screen.get_default():
        print("No Screen Found, Exiting...", file=sys.stderr)
        sys.exit(1)

    from kupfer.ui import browser  # pylint: disable=import-outside-toplevel

    wctrl = browser.WindowController()
    wctrl.main(quiet=quiet)


def main() -> None:
    # parse commandline before importing UI
    cli_opts = get_options()
    print_banner()

    # pylint: disable=import-outside-toplevel
    from kupfer import version
    from kupfer.support import pretty

    if "--debug" in cli_opts:
        pretty.DEBUG = True
        pretty.print_debug(
            __name__, "Version:", version.PACKAGE_NAME, version.VERSION
        )
        with suppress(ImportError):
            import debug

            debug.install()

    # enable colors only on terminal
    pretty.COLORS = sys.stdout.isatty() and "--no-colors" not in cli_opts

    sys.excepthook = sys.__excepthook__
    _set_process_title()

    quiet = "--no-splash" in cli_opts
    gtkmain(browser_start, quiet)
