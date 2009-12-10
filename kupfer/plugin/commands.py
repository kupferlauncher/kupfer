import os
# import symbols in tight loop to local namespace
from os import access, R_OK, X_OK, path

import gobject

from kupfer.objects import TextSource, Leaf
from kupfer.objects import TextLeaf, Execute
from kupfer import utils, icons

__kupfer_name__ = _("Shell Commands")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _("Run commandline programs")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class Command (TextLeaf):
	def __init__(self, exepath, name):
		TextLeaf.__init__(self, name, name)
		self.exepath = exepath

	def get_actions(self):
		yield Execute(quoted=False)
		yield Execute(in_terminal=True, quoted=False)

	def get_description(self):
		args = u" ".join(unicode(self).split(None, 1)[1:])
		return u"%s %s" % (self.exepath, args)

	def get_gicon(self):
		return icons.get_gicon_for_file(self.exepath)

	def get_icon_name(self):
		return "exec"

class CommandTextSource (TextSource):
	"""Yield path and command text items """
	def __init__(self):
		TextSource.__init__(self, name=_("Shell Commands"))

	def get_rank(self):
		return 80

	def get_items(self, text):
		if not text.strip():
			return
		if len(text.splitlines()) > 1:
			return
		firstword = text.split()[0]
		if firstword.startswith("/"):
			return
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
