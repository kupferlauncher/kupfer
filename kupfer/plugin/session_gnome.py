from kupfer.plugin import session_support as support

__kupfer_name__ = _("Gnome Session Manager")
__kupfer_sources__ = ("GnomeItemsSource", )
__description__ = _("Special items and actions for Gnome environment")
__version__ = "2009-12-05"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


LOGOUT_CMD = ("gnome-panel-logout", "gnome-session-save --kill")
SHUTDOWN_CMD = ("gnome-panel-logout --shutdown", 
		"gnome-session-save --shutdown-dialog")
LOCKSCREEN_CMD = ("gnome-screensaver-command --lock", "xdg-screensaver lock")

class GnomeItemsSource (support.CommonSource):
	def get_items(self):
		return (
			support.Logout(LOGOUT_CMD),
			support.LockScreen(LOCKSCREEN_CMD),
			support.Shutdown(SHUTDOWN_CMD),
		)

