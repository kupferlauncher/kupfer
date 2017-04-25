__kupfer_name__ = _("MATE Session Management")
__kupfer_sources__ = ("MateItemsSource", )
__description__ = _("Special items and actions for MATE environment")
__version__ = "2013-04-28"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.plugin import session_support as support

# sequences of argument lists
LOGOUT_CMD = (["mate-panel-logout"],
              ["mate-session-save", "--kill"])
SHUTDOWN_CMD = (["mate-panel-logout", "--shutdown"],
                ["mate-session-save", "--shutdown-dialog"])
LOCKSCREEN_CMD = (["mate-screensaver-command", "--lock"],
                  ["xdg-screensaver", "lock"])

class MateItemsSource (support.CommonSource):
	def __init__(self):
		support.CommonSource.__init__(self, _("MATE Session Management"))
	def get_items(self):
		return (
			support.Logout(LOGOUT_CMD),
			support.LockScreen(LOCKSCREEN_CMD),
			support.Shutdown(SHUTDOWN_CMD),
		)

