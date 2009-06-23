from kupfer.objects import Source, AppLeaf

__kupfer_sources__ = ("AppSource", )
__description__ = _("All applications and preferences")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class AppSource (Source):
	"""
	Applications source

	This Source contains all user-visible applications (as given by
	the desktop files)
	"""
	def __init__(self):
		super(AppSource, self).__init__(_("All Applications"))
	
	def get_items(self):
		from gio import app_info_get_all
		# Choosing only item.should_show() items misses all Preference applets
		# so we use a slight heurestic
		taken = set()
		for item in app_info_get_all():
			if item.should_show():
				yield AppLeaf(item)
				taken.add(item.get_executable())
		# Re-run and take some more
		for item in app_info_get_all():
			if (not item.should_show() and item.get_executable() not in taken
					and (not item.supports_files() and not
						item.supports_uris())):
				yield AppLeaf(item)
				taken.add(item.get_executable())

	def get_description(self):
		return _("All applications and preferences")

	def get_icon_name(self):
		return "gnome-applications"

