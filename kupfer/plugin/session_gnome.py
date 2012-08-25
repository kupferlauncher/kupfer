__kupfer_name__ = _("GNOME Session Management")
__kupfer_sources__ = ("GnomeItemsSource", )
__description__ = _("Special items and actions for GNOME environment")
__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from kupfer.plugin import session_support as support


# sequences of argument lists
LOGOUT_CMD = (["gnome-panel-logout"],
              ["gnome-session-save", "--kill"],
              ["gnome-session-quit", "--logout"])
SHUTDOWN_CMD = (["gnome-panel-logout", "--shutdown"],
                ["gnome-session-save", "--shutdown-dialog"],
                ["gnome-session-quit", "--power-off"])
LOCKSCREEN_CMD = (["gnome-screensaver-command", "--lock"],
                  ["xdg-screensaver", "lock"])

class GnomeItemsSource (support.CommonSource):
	def __init__(self):
		support.CommonSource.__init__(self, _("GNOME Session Management"))
	def get_items(self):
		return (
			support.Logout(LOGOUT_CMD),
			support.LockScreen(LOCKSCREEN_CMD),
			support.Shutdown(SHUTDOWN_CMD),
		)

