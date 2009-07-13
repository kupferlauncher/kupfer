
from kupfer.objects import Source, AppLeaf
from kupfer import launch

__kupfer_name__ = _("Running Applications")
__kupfer_sources__ = ("RunningApplicationsSource",)
__description__ = _("Currently active applications")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class RunningApplicationsSource (Source):
	"""List currently running applications """
	def __init__(self):
		Source.__init__(self, _("Running Applications"))
		from gio.unix import desktop_app_info_set_desktop_env
		desktop_app_info_set_desktop_env("GNOME")
	def is_dynamic(self):
		return True

	def get_items(self):
		from gio import app_info_get_all
		svc = launch.GetApplicationsMatcherService()
		is_running = svc.application_is_running
		return (AppLeaf(ai) for ai in app_info_get_all()
				if is_running(ai.get_id()))

	def get_description(self):
		return _("Running applications")

	def get_icon_name(self):
		return "gnome-applications"

