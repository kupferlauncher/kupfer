import subprocess

import glib
import gtk

from kupfer.objects import Action
from kupfer.objects import TextLeaf
from kupfer import kupferstring, task, uiutils

__kupfer_name__ = _("APT")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = ("ShowPackageInfo", )
__description__ = _("Interface with the package manager APT")
__version__ = ""
__author__ = ("VCoolio <martinkoelewijn@gmail.com>, "
              "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>")

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
	def valid_for_item(self, item):
		# check if it is a single word
		text = item.object
		return len(text.split(None, 1)) == 1

	def get_icon_name(self):
		return "synaptic"

