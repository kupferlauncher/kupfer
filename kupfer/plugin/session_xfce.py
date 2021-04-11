# -*- coding: utf-8 -*

__kupfer_name__ = _("XFCE Session Management")
__kupfer_sources__ = ("XfceItemsSource", )
__description__ = _("Special items and actions for XFCE environment")
__version__ = "2021-04-11"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

from kupfer.plugin import session_support as support
from kupfer import plugin_support

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "lock_cmd",
        "label": _("Screen lock command"),
        "type": str,
        "value": "xflock4",
    },
)

# sequences of argument lists
LOGOUT_CMD = (["xfce4-session-logout", "--logout"],)
SHUTDOWN_CMD = (["xfce4-session-logout"],)


class XfceItemsSource (support.CommonSource):
    def __init__(self):
        support.CommonSource.__init__(self, _("XFCE Session Management"))

    def get_items(self):
        lockscreen_cmd = __kupfer_settings__['lock_cmd'] \
            or "xdg-screensaver lock"

        return (
            support.Logout(LOGOUT_CMD),
            support.LockScreen((lockscreen_cmd.split(" "), )),
            support.Shutdown(SHUTDOWN_CMD),
        )
