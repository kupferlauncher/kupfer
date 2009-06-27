import os
# import symbols in tight loop to local namespace
from os import access, R_OK, X_OK, path

from kupfer.objects import TextSource, FileLeaf

__kupfer_sources__ = ()
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _("Execute programs in $PATH")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class CommandTextSource (TextSource):
	"""Yield path and command text items """
	def __init__(self):
		TextSource.__init__(self, name=_("Shell commands"))

	def get_rank(self):
		return 60

	def get_items(self, text):
		if not text:
			return
		# iterate over $PATH directories
		PATH = os.environ.get("PATH") or os.defpath
		for execdir in PATH.split(os.pathsep):
			exepath = path.join(execdir, text)
			if access(exepath, R_OK | X_OK) and path.isfile(exepath):
				yield FileLeaf(exepath)
				break
