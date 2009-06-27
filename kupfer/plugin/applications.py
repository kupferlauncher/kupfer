import xdg

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
		import xdg.BaseDirectory as base
		import xdg.DesktopEntry as desk
		# Choosing only item.should_show() items misses all Preference applets
		# so we use a slight heurestic
		whitelist = ["nautilus-cd-burner.desktop"]
		for item in app_info_get_all():
			if item.should_show() or item.get_id() in whitelist:
				yield AppLeaf(item)
			else:
				# Use Desktop file API to read its categories
				loc = list(base.load_data_paths("applications", item.get_id()))
				if not loc:
					print "No LOCATION FOUND for", item
					continue
				loc = loc[0]
				de = desk.DesktopEntry(loc)
				categories = de.getCategories()
				if "Settings" in categories and not de.getNoDisplay():
					yield AppLeaf(item)

	def get_description(self):
		return _("All applications and preferences")

	def get_icon_name(self):
		return "gnome-applications"

