# -*- coding: utf-8 -*

__kupfer_name__ = _("LXQT Session Management")
__kupfer_sources__ = ("LxqtItemsSource", )
__description__ = _("Actions for LXQT desktop")
__version__ = "2020-08-23"
__author__ = "Leonardo Masuero <leom255255@gmail.com>"
# Based on XFCE Session Management by Karol Będkowski

from kupfer.plugin import session_support as support


# sequences of argument lists
LOGOUT_CMD = (["lxqt-leave", "--logout"],)
SHUTDOWN_CMD = (["lxqt-leave", "--shutdown"],)
LOCKSCREEN_CMD = (["lxqt-leave", "--lockscreen"], )


class LxqtItemsSource (support.CommonSource):
    def __init__(self):
        support.CommonSource.__init__(self, _("LXQT Session Management"))
    def get_items(self):
        return (
            support.Logout(LOGOUT_CMD),
            support.LockScreen(LOCKSCREEN_CMD),
            support.Shutdown(SHUTDOWN_CMD),
        )
