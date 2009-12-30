import gio

from kupfer.objects import Source, AppLeaf
from kupfer import launch
from kupfer import plugin_support

__kupfer_name__ = _("Running Applications")
__kupfer_sources__ = ("RunningApplicationsSource",)
__description__ = _("Currently active applications")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)

class RunningApplicationsSource (Source):
	"""List currently running applications """
	def __init__(self):
		Source.__init__(self, _("Running Applications"))
		self.all_apps = []

	def initialize(self):
		self.all_apps = gio.app_info_get_all()

	def is_dynamic(self):
		return True

	def get_items(self):
		is_running = launch.application_is_running
		return (AppLeaf(ai) for ai in self.all_apps if is_running(ai))

	def get_description(self):
		return _("Running applications")

	def get_icon_name(self):
		return "gnome-applications"

