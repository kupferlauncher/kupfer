
__kupfer_name__ = _("Applications")
__kupfer_sources__ = ("AppSource", )
__kupfer_actions__ = (
		"OpenWith",
		"SetDefaultApplication",
	)
__description__ = _("All applications and preferences")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import gio
from gio import app_info_get_all
#from gio.unix import desktop_app_info_set_desktop_env

from kupfer.objects import Action, Source, AppLeaf, FileLeaf
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer import config, plugin_support

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "desktop_type",
		"label": _("Applications for Desktop Environment"),
		"type": str,
		"value": "GNOME",
		"alternatives": ("GNOME", "KDE", "LXDE", "ROX", "XFCE")
	},
)

class AppSource (Source, FilesystemWatchMixin):
	"""
	Applications source

	This Source contains all user-visible applications (as given by
	the desktop files)
	"""
	def __init__(self):
		super(AppSource, self).__init__(_("Applications"))

	def initialize(self):
		application_dirs = config.get_data_dirs("", "applications")
		self.monitor_token = self.monitor_directories(*application_dirs)

	def get_items(self):
		# If we set proper desktop environment
		# We get exactly the apps shown in the menu,
		# as well as the preference panes
		desktop_type = __kupfer_settings__["desktop_type"]
		gio.DesktopAppInfo.set_desktop_env(desktop_type)
		#desktop_app_info_set_desktop_env(desktop_type)
		# Add this to the default
		whitelist = set([
			# if you set/reset default handler for folders it is useful
			"nautilus-folder-handler.desktop",
			# we think that these are useful to show
			"eog.desktop",
			"evince.desktop",
			"gnome-about.desktop",
			"gstreamer-properties.desktop",
			"notification-properties.desktop",
			])
		blacklist = set([
			"nautilus-home.desktop",
		])

		for item in app_info_get_all():
			id_ = item.get_id()
			if id_ in whitelist or (item.should_show() and not id_ in blacklist):
				yield AppLeaf(item)

	def should_sort_lexically(self):
		return True

	def get_description(self):
		return _("All applications and preferences")

	def get_icon_name(self):
		return "applications-office"
	def provides(self):
		yield AppLeaf

class OpenWith (Action):
	def __init__(self):
		Action.__init__(self, _("Open With..."))

	def _activate(self, app_leaf, paths, ctx):
		app_leaf.launch(paths=paths, ctx=ctx)

	def wants_context(self):
		return True

	def activate(self, leaf, iobj, ctx):
		self._activate(iobj, (leaf.object, ), ctx)
	def activate_multiple(self, objects, iobjects, ctx):
		# for each application, launch all the files
		for iobj_app in iobjects:
			self._activate(iobj_app, [L.object for L in objects], ctx)

	def item_types(self):
		yield FileLeaf
	def requires_object(self):
		return True
	def object_types(self):
		yield AppLeaf
	def get_description(self):
		return _("Open with any application")

class SetDefaultApplication (Action):
	def __init__(self):
		Action.__init__(self, _("Set Default Application..."))
	def activate(self, leaf, obj):
		gfile = gio.File(leaf.object)
		info = gfile.query_info(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
		content_type = info.get_attribute_string(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
		print(content_type, gfile)
		desktop_item = obj.object
		desktop_item.set_as_default_for_type(content_type)
	def item_types(self):
		yield FileLeaf
	def requires_object(self):
		return True
	def object_types(self):
		yield AppLeaf
	def get_description(self):
		return _("Set default application to open this file type")
