__kupfer_name__ = _("Gnome Terminal Profiles")
__kupfer_sources__ = ("SessionsSource", )
__description__ = _("Launch Gnome Terminal profiles")
__version__ = ""
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import os

import gconf
import glib

from kupfer.objects import Leaf, Action
from kupfer.obj.apps import ApplicationSource
from kupfer import utils, icons, plugin_support

__kupfer_plugin_category__ = [ plugin_support.CATEGORY_ENV_X,
		plugin_support.CATEGORY_ENV_GNOME
]

GCONF_KEY = "/apps/gnome-terminal/profiles"


class Terminal(Leaf):
	""" Leaf represent profile saved in Gnome Terminal"""

	def __init__(self, name):
		Leaf.__init__(self, name, name)

	def get_actions(self):
		yield OpenSession()

	def get_icon_name(self):
		return "terminal"


class OpenSession(Action):
	""" Opens Gnome Terminal profile """
	def __init__(self):
		Action.__init__(self, _("Open"))

	def activate(self, leaf):
		utils.spawn_async(["gnome-terminal",
				   "--profile=%s" % leaf.object],
				  in_dir=os.path.expanduser("~"))

	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "terminal")


class SessionsSource(ApplicationSource):
	""" Yield Gnome Terminal profiles """
	appleaf_content_id = 'gnome-terminal'

	def __init__(self):
		ApplicationSource.__init__(self, name=_("Gnome Terminal Profiles"))

	def get_items(self):
		gc = gconf.client_get_default()
		try:
			if not gc.dir_exists(GCONF_KEY):
				return

			for entry in gc.all_dirs(GCONF_KEY):
				yield Terminal(gc.get_string("%s/visible_name" % entry))
		except glib.GError, err:
			self.output_error(err)

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield Terminal

# Local Variables: ***
# python-indent: 8 ***
# indent-tabs-mode: t ***
# End: ***
