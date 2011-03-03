__kupfer_name__ = _("Shell Commands")
__kupfer_sources__ = ()
__kupfer_actions__ = (
		"PassToCommand",
		"FilterThroughCommand",
		"WriteToCommand",
	)
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _("Run commandline programs")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import shlex

import gobject

from kupfer.objects import TextSource, Leaf, TextLeaf, Action, FileLeaf
from kupfer.objects import OperationError
from kupfer.obj.fileactions import Execute
from kupfer import utils, icons
from kupfer import commandexec
from kupfer import kupferstring
from kupfer import pretty

def unicode_shlex_split(ustr, **kwargs):
	"""shlex.split is depressingly broken on unicode input"""
	s_str = ustr.encode("UTF-8")
	return [kupferstring.tounicode(t) for t in shlex.split(s_str, **kwargs)]

def rm_quotes(us):
	"""Remove "quotes" -> quotes if wrapped in " or ' quotes"""
	if len(us) > 1 and us[0] in ("'", '"') and us[0] == us[-1]:
		return us[1:-1]
	return us

def custom_shlex_split(ustr):
	# Use posix=False so that we don't swallow backslashes "\"
	# After that we have to remove quotes ourselves
	return map(rm_quotes, unicode_shlex_split(ustr, posix=False))

def get_commandline_argv(commandline):
	""" Use shlex to allow simple quoting in the commandline """
	try:
		argv = custom_shlex_split(commandline)
	except ValueError:
		# Exception raised on unpaired quotation marks
		argv = commandline.split(None, 1)
	return argv

def finish_command(token, acommand, stdout, stderr, post_result=True):
	"""Show async error if @acommand returns error output & error status.
	Else post async result if @post_result.
	"""
	max_error_msg=512
	pretty.print_debug(__name__, "Exited:", acommand)
	ctx = commandexec.DefaultActionExecutionContext()
	if acommand.exit_status != 0 and not stdout and stderr:
		try:
			errstr = kupferstring.fromlocale(stderr)[:max_error_msg]
			raise OperationError(errstr)
		except OperationError:
			ctx.register_late_error(token)
	elif post_result:
		leaf = TextLeaf(kupferstring.fromlocale(stdout))
		ctx.register_late_result(token, leaf)


class GetOutput (Action):
	def __init__(self):
		Action.__init__(self, _("Run (Get Output)"))

	def activate(self, leaf):
		argv = get_commandline_argv(leaf.object)
		ctx = commandexec.DefaultActionExecutionContext()
		token = ctx.get_async_token()
		pretty.print_debug(__name__, "Spawning with timeout 15 seconds")
		acom = utils.AsyncCommand(argv, self.finish_callback, 15)
		acom.token = token

	def finish_callback(self, acommand, stdout, stderr):
		finish_command(acommand.token, acommand, stdout, stderr)

	def get_description(self):
		return _("Run program and return its output")

class PassToCommand (Action):
	def __init__(self):
		Action.__init__(self, _("Pass to Command..."))

	def activate(self, leaf, iobj):
		self.activate_multiple((leaf,),(iobj, ))

	def _run_command(self, objs, iobj):
		if isinstance(iobj, Command):
			argv = get_commandline_argv(iobj.object)
		else:
			argv = [iobj.object]
		argv.extend([o.object for o in objs])
		ctx = commandexec.DefaultActionExecutionContext()
		token = ctx.get_async_token()
		pretty.print_debug(__name__, "Spawning without timeout")
		acom = utils.AsyncCommand(argv, self.finish_callback, None)
		acom.token = token

	def activate_multiple(self, objs, iobjs):
		for iobj in iobjs:
			self._run_command(objs, iobj)

	def item_types(self):
		yield TextLeaf
		yield FileLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield FileLeaf
		yield Command

	def valid_object(self, iobj, for_item=None):
		if isinstance(iobj, Command):
			return True
		return not iobj.is_dir() and os.access(iobj.object, os.X_OK | os.R_OK)

	def finish_callback(self, acommand, stdout, stderr):
		finish_command(acommand.token, acommand, stdout, stderr, False)

	def get_description(self):
		return _("Run program with object as an additional parameter")


class WriteToCommand (Action):
	def __init__(self):
		Action.__init__(self, _("Send to Command..."))

	def activate(self, leaf, iobj):
		if isinstance(iobj, Command):
			argv = get_commandline_argv(iobj.object)
		else:
			argv = [iobj.object]
		ctx = commandexec.DefaultActionExecutionContext()
		token = ctx.get_async_token()
		pretty.print_debug(__name__, "Spawning without timeout")
		acom = utils.AsyncCommand(argv, self.finish_callback, None,
		                          stdin=leaf.object)
		acom.token = token

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield FileLeaf
		yield Command

	def valid_object(self, iobj, for_item=None):
		if isinstance(iobj, Command):
			return True
		return not iobj.is_dir() and os.access(iobj.object, os.X_OK | os.R_OK)

	def finish_callback(self, acommand, stdout, stderr):
		finish_command(acommand.token, acommand, stdout, stderr, False)

	def get_description(self):
		return _("Run program and supply text on the standard input")

class FilterThroughCommand (WriteToCommand):
	def __init__(self):
		Action.__init__(self, _("Filter through Command..."))

	def finish_callback(self, acommand, stdout, stderr):
		finish_command(acommand.token, acommand, stdout, stderr)

	def get_description(self):
		return _("Run program and supply text on the standard input")

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
