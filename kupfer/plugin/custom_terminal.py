__kupfer_name__ = _("Custom Terminal")
__description__ = _("""Configure a custom terminal emulator.

The plugin adds another terminal alternative (select it on the main page).""")
__version__ = ""
__author__ = "Ulrik Sverdrup"

from kupfer import plugin_support
from kupfer import utils

__kupfer_settings__ = plugin_support.PluginSettings(
        {
            "key": "command",
            "label": _("Command"),
            "type": str,
            "value": "",
        },
        {
            "key": "exearg",
            "label": _("Execute flag"),
            "type": str,
            "value": "-e",
            "tooltip": ("The flag which makes the terminal execute"
                        " everything following it in the argument string. ")
        },
    )



def initialize_plugin(name):
    __kupfer_settings__.connect_settings_changed_cb(_update_alternative)
    _update_alternative()

def _update_alternative(*args):
    command = __kupfer_settings__["command"]
    exearg = __kupfer_settings__["exearg"]
    argv = utils.argv_for_commandline(command)
    if not argv or not utils.lookup_exec_path(argv[0]):
        return
    plugin_support.register_alternative(__name__, 'terminal', 'custom1',
            name=_("Custom Terminal"),
            argv=argv,
            exearg=exearg,
            desktopid="",
            startup_notify=True)

