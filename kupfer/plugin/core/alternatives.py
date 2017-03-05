from kupfer import plugin_support
from kupfer import icons

def initialize_alternatives(__name__):
    plugin_support.register_alternative(__name__, 'icon_renderer', 'gtk',
        **{
            'name': _("GTK+"),
            'renderer': icons.IconRenderer,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'gnome-terminal',
        **{
            'name': _("GNOME Terminal"),
            'argv': ['gnome-terminal'],
            'exearg': '-x',
            'desktopid': "gnome-terminal.desktop",
            'startup_notify': True,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'xfce4-terminal',
        **{
            'name': _("XFCE Terminal"),
            'argv': ['xfce4-terminal'],
            'exearg': '-x',
            'desktopid': "xfce4-terminal.desktop",
            'startup_notify': True,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'exo-open',
        **{
            'name': "exo-open",
            'argv': ['exo-open', '--launch', 'TerminalEmulator'],
            'exearg': '',
            'desktopid': "",
            'startup_notify': False,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'lxterminal',
        **{
            'name': _("LXTerminal"),
            'argv': ['lxterminal'],
            'exearg': '-e',
            'desktopid': "lxterminal.desktop",
            'startup_notify': False,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'xterm',
        **{
            'name': _("X Terminal"),
            'argv': ['xterm'],
            'exearg': '-e',
            'desktopid': "xterm.desktop",
            'startup_notify': False,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'x-terminal-emulator',
        **{
            'name': 'x-terminal-emulator',
            'argv': ['x-terminal-emulator'],
            'exearg': '-e',
            'desktopid': "",
            'startup_notify': False,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'urxvt',
        **{
            'name': _("Urxvt"),
            'argv': ['urxvt'],
            'exearg': '-e',
            'desktopid': "urxvt.desktop",
            'startup_notify': False,
        })

    plugin_support.register_alternative(__name__, 'terminal', 'konsole',
        **{
            'name': _("Konsole"),
            'argv': ['konsole'],
            'exearg': '-e',
            'desktopid': "konsole.desktop",
            # Not sure here, so setting to false
            'startup_notify': False,
        })
