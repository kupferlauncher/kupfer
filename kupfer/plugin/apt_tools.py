import subprocess

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf
from kupfer import icons, kupferstring, task, uiutils, utils
from kupfer import plugin_support

__kupfer_name__ = _("APT")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"ShowPackageInfo",
		"SearchPackageName",
		"InstallPackage",
	)
__description__ = _("Interface with the package manager APT")
__version__ = ""
__author__ = ("Martin Koelewijn <martinkoelewijn@gmail.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>")

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "installation_method",
		"label": _("Installation method"),
		"type": str,
		"value": "gksu apt-get install",
	},
)

class InfoTask(task.ThreadTask):
	def __init__(self, text):
		super(InfoTask, self).__init__()
		self.text = text
	def thread_do(self):
		P = subprocess.PIPE
		apt = subprocess.Popen("aptitude show '%s'" % self.text, shell=True,
				stdout=P, stderr=P)
		acp = subprocess.Popen("apt-cache policy '%s'" % self.text, shell=True,
				stdout=P, stderr=P)
		apt_out, apt_err = apt.communicate()
		acp_out, acp_err = acp.communicate()
		# Commandline output is encoded according to locale
		self.info = u"".join(kupferstring.fromlocale(s)
				for s in (apt_err, acp_err, apt_out, acp_out))
	def thread_finish(self):
		uiutils.show_text_result(self.info, title=_("Show Package Information"))

class ShowPackageInfo (Action):
	def __init__(self):
		Action.__init__(self, _("Show Package Information"))

	def is_async(self):
		return True
	def activate(self, leaf):
		return InfoTask(leaf.object.strip())

	def item_types(self):
		yield TextLeaf
		yield Package

	def valid_for_item(self, item):
		# check if it is a single word
		text = item.object
		return len(text.split(None, 1)) == 1

	def get_gicon(self):
		return icons.ComposedIcon("dialog-information", "package")

class InstallPackage (Action):
	def __init__(self):
		Action.__init__(self, _("Install"))
	def activate(self, leaf):
		pkg = leaf.object.strip()
		cli = "%s %s" % (__kupfer_settings__["installation_method"], pkg)
		utils.launch_commandline(cli, in_terminal=True)

	def item_types(self):
		yield Package
		yield TextLeaf

	def get_description(self):
		return _("Install package using the configured method")
	def get_icon_name(self):
		return "gtk-save"

class Package (Leaf):
	def __init__(self, package, desc):
		Leaf.__init__(self, package, package)
		self.desc = desc

	def get_description(self):
		return self.desc
	def get_icon_name(self):
		return "package"

class PackageSearchSource (Source):
	def __init__(self, query):
		self.query = query
		Source.__init__(self, _('Packages matching "%s"') % query)

	def get_items(self):
		package = self.query
		P = subprocess.PIPE
		acp = subprocess.Popen("apt-cache search --names-only '%s'" % package,
				shell=True, stdout=P, stderr=P)
		acp_out, acp_err = acp.communicate()
		for line in kupferstring.fromlocale(acp_out).splitlines():
			if not line.strip():
				continue
			package, desc = line.split(" - ", 1)
			yield Package(package, desc)

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield TextLeaf
	def get_icon_name(self):
		return "system-software-install"

class SearchPackageName (Action):
	def __init__(self):
		Action.__init__(self, _("Search Package Name..."))

	def is_factory(self):
		return True

	def activate(self, leaf):
		package = leaf.object.strip()
		return PackageSearchSource(package)

	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, item):
		# check if it is a single word
		text = item.object
		return len(text.split(None, 1)) == 1

	def get_icon_name(self):
		return "system-software-install"

