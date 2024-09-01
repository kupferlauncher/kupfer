import typing as ty

from gi.repository import Gio

from kupfer import icons, plugin_support
from kupfer.support import desktop_parse

if ty.TYPE_CHECKING:
    from gettext import gettext as _


def initialize_alternatives(name):
    plugin_support.register_alternative(
        name,
        "icon_renderer",
        "gtk",
        name=_("GTK+"),
        renderer=icons.IconRenderer,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "gnome-terminal",
        name=_("GNOME Terminal"),
        argv=["gnome-terminal"],
        exearg="-x",
        desktopid="gnome-terminal.desktop",
        startup_notify=True,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "xfce4-terminal",
        name=_("XFCE Terminal"),
        argv=["xfce4-terminal"],
        exearg="-x",
        desktopid="xfce4-terminal.desktop",
        startup_notify=True,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "exo-open",
        name="exo-open",
        argv=["exo-open", "--launch", "TerminalEmulator"],
        exearg="",
        desktopid="",
        startup_notify=False,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "lxterminal",
        name=_("LXTerminal"),
        argv=["lxterminal"],
        exearg="-e",
        desktopid="lxterminal.desktop",
        startup_notify=False,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "xterm",
        name=_("X Terminal"),
        argv=["xterm"],
        exearg="-e",
        desktopid="xterm.desktop",
        startup_notify=False,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "x-terminal-emulator",
        name="x-terminal-emulator",
        argv=["x-terminal-emulator"],
        exearg="-e",
        desktopid="",
        startup_notify=False,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "urxvt",
        name=_("Urxvt"),
        argv=["urxvt"],
        exearg="-e",
        desktopid="urxvt.desktop",
        startup_notify=False,
    )

    plugin_support.register_alternative(
        name,
        "terminal",
        "konsole",
        name=_("Konsole"),
        argv=["konsole"],
        exearg="-e",
        desktopid="konsole.desktop",
        # Not sure here, so setting to false
        startup_notify=False,
    )

    _register_terminal_emulators(name)
    _register_text_editors(name)


def _register_text_editors(name):
    plugin_support.register_alternative(
        name,
        "editor",
        "sys-editor",
        name=_("System `editor`"),
        argv=["editor"],
        terminal=True,
    )

    # find all applications that support text/plain and register it
    # as text editors

    for app in Gio.app_info_get_all_for_type("text/plain"):
        app_id = app.get_id()
        cmd = app.get_commandline()
        args = desktop_parse.parse_argv(cmd)

        plugin_support.register_alternative(
            name,
            "editor",
            app_id.removesuffix(".desktop"),
            name=app.get_display_name(),
            argv=args,
            terminal=app.get_boolean("Terminal"),
        )


def _register_terminal_emulators(name):
    """Find all applications with category 'TerminalEmulator' and register
    it as terminal alternative."""

    # hard coded skip-list for already defined above terminals but with
    # different id
    skip = ("debian-uxterm.desktop", "debian-xterm.desktop")

    for app in Gio.app_info_get_all():
        app_id = app.get_id()
        if app_id in skip:
            continue

        if "TerminalEmulator" not in (app.get_categories() or ""):
            continue

        cmd = app.get_commandline()
        args = desktop_parse.parse_argv(cmd)

        plugin_support.register_alternative(
            name,
            "terminal",
            app_id.removesuffix(".desktop"),
            name=app.get_display_name(),
            argv=args,
            exearg="",
            desktopid=app_id,
            startup_notify=False,
        )
