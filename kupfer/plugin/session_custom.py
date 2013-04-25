__kupfer_name__ = _("Custom Session Management")
__kupfer_sources__ = ("ItemSource",)
__description__ = _("Run custom session management commands")
__version__ = "2"
__author__ = "Joseph Lansdowne <J49137@gmail.com>"

import shlex

from kupfer.plugin_support import PluginSettings
from kupfer.plugin import session_support as support

__kupfer_settings__ = PluginSettings(
	{
		"key": "logout",
		"label": _("Log out"),
		"type": str,
		"value": ""
	}, {
		"key": "switchuser",
		"label": _("Switch user"),
		"type": str,
		"value": ""
	}, {
		"key": "lockscreen",
		"label": _("Lock screen"),
		"type": str,
		"value": ""
	}, {
		"key": "shutdown",
		"label": _("Shut down"),
		"type": str,
		"value": ""
	}, {
		"key": "reboot",
		"label": _("Restart"),
		"type": str,
		"value": ""
	}, {
		"key": "suspend",
		"label": _("Suspend"),
		"type": str,
		"value": ""
	}
)


class ItemSource (support.CommonSource):

	def __init__(self):
		support.CommonSource.__init__(self, _("Custom Session Management"))

	def get_items(self):
		for item in ("Logout", "SwitchUser", "LockScreen", "Shutdown",
					 "Reboot", "Suspend"):
			value = __kupfer_settings__[item.lower()].strip()
			if value:
				argv = shlex.split(value)
				# session_support Leafs take list of argument lists as
				# fallbacks
				yield getattr(support, item)((argv,))
