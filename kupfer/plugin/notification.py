__kupfer_name__ = _("Show Notification")
__kupfer_actions__ = (
		"ShowNotification",
	)
__description__ = ""
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import pynotify

from kupfer.objects import Action
from kupfer.objects import TextLeaf
from kupfer import textutils, plugin_support

__kupfer_plugin_category__ = plugin_support.CATEGORY_KUPFER


def show_notification(title, body, icon_name=None, critical=False):
	if not pynotify.is_initted():
		pynotify.init("kupfer")
	notification = pynotify.Notification(title)
	if body:
		notification.set_property("body", body)
	if icon_name:
		notification.set_property("icon-name", icon_name)
	if critical:
		notification.set_urgency(pynotify.URGENCY_CRITICAL)
	notification.show()


class ShowNotification (Action):
	def __init__(self):
		Action.__init__(self, _("Show Notification"))

	def activate(self, leaf):
		title, body = textutils.extract_title_body(leaf.object)
		if body:
			show_notification(title, body, icon_name=self.get_icon_name())
		else:
			show_notification(title, None)

	def item_types(self):
		#if plugin_support.has_capability("NOTIFICATION"):
		yield TextLeaf

	def get_icon_name(self):
		return "gtk-bold"

