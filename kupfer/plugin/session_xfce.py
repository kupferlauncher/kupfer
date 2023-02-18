__kupfer_name__ = _("XFCE Session Management")
__kupfer_sources__ = ("XfceItemsSource",)
__description__ = _("Special items and actions for XFCE environment")
__version__ = "2021-04-11"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

from kupfer import plugin_support
from kupfer.plugin import session_support as support

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "lock_cmd",
        "label": _("Screen lock command"),
        "type": str,
        "value": "xflock4",
    },
)

# sequences of argument lists
_LOGOUT_CMD = (["xfce4-session-logout", "--logout"],)
_SHUTDOWN_CMD = (["xfce4-session-logout"],)


class XfceItemsSource(support.CommonSource):
    def __init__(self):
        support.CommonSource.__init__(self, _("XFCE Session Management"))

    def get_items(self):
        lockscreen_cmd = (
            __kupfer_settings__["lock_cmd"] or "xdg-screensaver lock"
        )

        return (
            support.Logout(_LOGOUT_CMD),
            support.LockScreen((lockscreen_cmd.split(" "),)),
            support.Shutdown(_SHUTDOWN_CMD),
        )
