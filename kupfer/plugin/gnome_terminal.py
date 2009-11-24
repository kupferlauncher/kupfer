import os

from kupfer.objects import Source, Leaf, Action, \
    AppLeafContentMixin, PicklingHelperMixin
from kupfer import utils, icons

__kupfer_name__ = _("Gnome Terminal Sessions")
__kupfer_sources__ = ("SessionsSource", )
__description__ = _("Launch Gnome Terminal sessions")
__version__ = ""
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import gconf

GCONF_KEY = "/apps/gnome-terminal/profiles"


class Terminal(Leaf):
	""" Leaf represent session saved in Gnome Terminal"""

	def __init__(self, name):
		Leaf.__init__(self, name, name)

	def get_actions(self):
		yield OpenSession()

	def get_icon_name(self):
		return "terminal"


class OpenSession(Action):
	""" Opens Gnome Terminal session """
	def __init__(self):
		Action.__init__(self, _("Open"))

	def activate(self, leaf):
		utils.spawn_async(["gnome-terminal",
				   "--profile=%s" % leaf.object],
				  in_dir=os.path.expanduser("~"))

	def get_gicon(self):
		return icons.ComposedIcon("gtk-execute", "terminal")


class SessionsSource(AppLeafContentMixin, Source, PicklingHelperMixin):
	""" Yield Gnome Terminal profiles """
	appleaf_content_id = 'gnome-terminal'

	def __init__(self):
		Source.__init__(self, name=_("Gnome Terminal Sessions"))

	def get_items(self):
		gc = gconf.client_get_default()
		if not gc.dir_exists(GCONF_KEY):
			return

		for entry in gc.all_dirs(GCONF_KEY):
			yield Terminal(gc.get_string("%s/visible_name" % entry))

	def should_sort_lexically(self):
		return True

# Local Variables: ***
# python-indent: 8 ***
# indent-tabs-mode: t ***
# End: ***
