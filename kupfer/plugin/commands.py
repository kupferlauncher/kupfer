import os
# import symbols in tight loop to local namespace
from os import access, R_OK, X_OK, path

import gobject

from kupfer.objects import TextSource, FileLeaf, Leaf, Execute
from kupfer import utils, icons

__kupfer_name__ = _("Shell commands")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _("Run commandline programs")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Command (Leaf):
	def __init__(self, obj, name):
		Leaf.__init__(self, obj, name)
		self.args = " ".join(name.split(" ", 1)[1:])

	def get_actions(self):
		yield Execute(args=self.args)
		yield Execute(in_terminal=True, args=self.args)

	def get_description(self):
		return "%s %s" % (self.object, self.args)
	def get_gicon(self):
		icons.get_gicon_for_file(self.object)
	def get_icon_name(self):
		return "exec"

class CommandTextSource (TextSource):
	"""Yield path and command text items """
	def __init__(self):
		TextSource.__init__(self, name=_("Shell commands"))

	def get_rank(self):
		return 80

	def get_items(self, text):
		if not text:
			return
		firstword = text.split()[0]
		# iterate over $PATH directories
		PATH = os.environ.get("PATH") or os.defpath
		for execdir in PATH.split(os.pathsep):
			exepath = path.join(execdir, firstword)
			# use filesystem encoding here
			exepath = gobject.filename_from_utf8(exepath)
			if access(exepath, R_OK | X_OK) and path.isfile(exepath):
				yield Command(exepath, text)
				break
	def get_description(self):
		return _("Run commandline programs")
