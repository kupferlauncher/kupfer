__kupfer_name__ = _("LXQT Session Management")
__kupfer_sources__ = ("LxqtItemsSource",)
__description__ = _("Actions for LXQT desktop")
__version__ = "2020-08-23"
__author__ = "Leonardo Masuero <leom255255@gmail.com>"
# Based on XFCE Session Management by Karol Będkowski
import typing as ty

from kupfer.plugin import session_support as support

if ty.TYPE_CHECKING:
    from gettext import gettext as _

# sequences of argument lists
_LOGOUT_CMD = (["lxqt-leave", "--logout"],)
_SHUTDOWN_CMD = (["lxqt-leave", "--shutdown"],)
_LOCKSCREEN_CMD = (["lxqt-leave", "--lockscreen"],)


class LxqtItemsSource(support.CommonSource):
    source_scan_interval: int = 36000

    def __init__(self):
        support.CommonSource.__init__(self, _("LXQT Session Management"))

    def get_items(self):
        return (
            support.Logout(_LOGOUT_CMD),
            support.LockScreen(_LOCKSCREEN_CMD),
            support.Shutdown(_SHUTDOWN_CMD),
        )
