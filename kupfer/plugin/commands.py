__kupfer_name__ = _("Shell Commands")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _("Run commandline programs")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import shlex

import gobject

from kupfer.objects import TextSource, Leaf, TextLeaf, Action
from kupfer.obj.fileactions import Execute
from kupfer import utils, icons
from kupfer import commandexec
from kupfer import kupferstring
from kupfer import pretty

def unicode_shlex_split(ustr, **kwargs):
	"""shlex.split is depressingly broken on unicode input"""
	s_str = ustr.encode("UTF-8")
	return [kupferstring.tounicode(t) for t in shlex.split(s_str, **kwargs)]


class GetOutput (Action):
	def __init__(self):
		Action.__init__(self, _("Run (Get Output)"))

	def activate(self, leaf):
		# use shlex to allow simple quoting
		commandline = leaf.object
		try:
			argv = unicode_shlex_split(commandline)
		except ValueError:
			# Exception raised on unpaired quotation marks
			argv = commandline.split(None, 1)
		ctx = commandexec.DefaultActionExecutionContext()
		token = ctx.get_async_token()
		pretty.print_debug(__name__, "Spawning with timeout 15 seconds")
		acom = utils.AsyncCommand(argv, self.finish_callback, 15)
		acom.token = token

	def finish_callback(self, acommand, stdout, stderr):
		ctx = commandexec.DefaultActionExecutionContext()
		leaf = TextLeaf(kupferstring.fromlocale(stdout))
		ctx.register_late_result(acommand.token, leaf)

	def get_description(self):
		return _("Run program and return its output")

class Command (TextLeaf):
	def __init__(self, exepath, name):
		TextLeaf.__init__(self, name, name)
		self.exepath = exepath

	def get_actions(self):
		yield Execute(quoted=False)
		yield Execute(in_terminal=True, quoted=False)
		yield GetOutput()

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

	def get_text_items(self, text):
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
			exepath = os.path.join(execdir, firstword)
			# use filesystem encoding here
			exepath = gobject.filename_from_utf8(exepath)
			if os.access(exepath, os.R_OK|os.X_OK) and os.path.isfile(exepath):
				yield Command(exepath, text)
				break
	def get_description(self):
		return _("Run commandline programs")
