# -*- coding: utf-8 -*

__kupfer_name__ = _("XFCE Session Management")
__kupfer_sources__ = ("XfceItemsSource", )
__description__ = _("Special items and actions for XFCE environment")
__version__ = "2009-12-05"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

from kupfer.plugin import session_support as support


# sequences of argument lists
LOGOUT_CMD = (["xfce4-session-logout", "--logout"],)
SHUTDOWN_CMD = (["xfce4-session-logout"],)
LOCKSCREEN_CMD = (["xdg-screensaver", "lock"], )


class XfceItemsSource (support.CommonSource):
    def __init__(self):
        support.CommonSource.__init__(self, _("XFCE Session Management"))
    def get_items(self):
        return (
            support.Logout(LOGOUT_CMD),
            support.LockScreen(LOCKSCREEN_CMD),
            support.Shutdown(SHUTDOWN_CMD),
        )
