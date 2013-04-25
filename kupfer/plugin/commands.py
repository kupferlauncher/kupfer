__kupfer_name__ = _("Shell Commands")
__kupfer_sources__ = ()
__kupfer_actions__ = (
		"PassToCommand",
		"FilterThroughCommand",
		"WriteToCommand",
	)
__kupfer_text_sources__ = ("CommandTextSource",)
__description__ = _(u"Run command-line programs. Actions marked with"
                    u" the symbol %s run in a subshell.") % u"\N{GEAR}"
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
import shlex
from pipes import quote
from subprocess import check_output

import gobject

from kupfer.objects import TextSource, TextLeaf, Action, FileLeaf
from kupfer.objects import OperationError
from kupfer.obj.fileactions import Execute
from kupfer import utils, icons
from kupfer import kupferstring
from kupfer import pretty
from kupfer import plugin_support

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		"key" : "aliases",
		"label": _("Include Bash aliases"),
		"type": bool,
		"value": False
	}, {
		"key" : "functions",
		"label": _("Include Bash functions"),
		"type": bool,
		"value": False
	}
)


def finish_command(ctx, acommand, stdout, stderr, post_result=True):
	"""Show async error if @acommand returns error output & error status.
	Else post async result if @post_result.
	"""
	max_error_msg=512
	pretty.print_debug(__name__, "Exited:", acommand)
	if acommand.exit_status != 0 and not stdout and stderr:
		errstr = kupferstring.fromlocale(stderr)[:max_error_msg]
		ctx.register_late_error(OperationError(errstr))
	elif post_result:
		leaf = TextLeaf(kupferstring.fromlocale(stdout))
		ctx.register_late_result(leaf)


class GetOutput (Action):
	def __init__(self):
		Action.__init__(self, _("Run (Get Output)"))

	def wants_context(self):
		return True

	def activate(self, leaf, ctx):
		if isinstance(leaf, Command):
			argv = ['sh', '-c', leaf.object, '--']
		else:
			argv = [leaf.object]

		def finish_callback(acommand, stdout, stderr):
			finish_command(ctx, acommand, stdout, stderr)

		pretty.print_debug(__name__, "Spawning with timeout 15 seconds")
		utils.AsyncCommand(argv, finish_callback, 15)

	def get_description(self):
		return _("Run program and return its output") + u" \N{GEAR}"

class PassToCommand (Action):
	def __init__(self):
		# TRANS: The user starts a program (command) and the text
		# TRANS: is an argument to the command
		Action.__init__(self, _("Pass to Command..."))

	def wants_context(self):
		return True

	def activate(self, leaf, iobj, ctx):
		self.activate_multiple((leaf,),(iobj, ), ctx)

	def _run_command(self, objs, iobj, ctx):
		if isinstance(iobj, Command):
			argv = ['sh', '-c', iobj.object + ' "$@"', '--']
		else:
			argv = [iobj.object]

		def finish_callback(acommand, stdout, stderr):
			finish_command(ctx, acommand, stdout, stderr, False)

		argv.extend([o.object for o in objs])
		pretty.print_debug(__name__, "Spawning without timeout")
		utils.AsyncCommand(argv, finish_callback, None)

	def activate_multiple(self, objs, iobjs, ctx):
		for iobj in iobjs:
			self._run_command(objs, iobj, ctx)

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

	def get_description(self):
		return _("Run program with object as an additional parameter") + \
		        u" \N{GEAR}"


class WriteToCommand (Action):
	def __init__(self):
		# TRANS: The user starts a program (command) and
		# TRANS: the text is written on stdin
		Action.__init__(self, _("Write to Command..."))
		self.post_result = False

	def wants_context(self):
		return True

	def activate(self, leaf, iobj, ctx):
		if isinstance(iobj, Command):
			argv = ['sh', '-c', iobj.object]
		else:
			argv = [iobj.object]

		def finish_callback(acommand, stdout, stderr):
			finish_command(ctx, acommand, stdout, stderr, self.post_result)

		pretty.print_debug(__name__, "Spawning without timeout")
		utils.AsyncCommand(argv, finish_callback, None, stdin=leaf.object)

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

	def get_description(self):
		return _("Run program and supply text on the standard input") + \
		        u" \N{GEAR}"

class FilterThroughCommand (WriteToCommand):
	def __init__(self):
		# TRANS: The user starts a program (command) and
		# TRANS: the text is written on stdin, and we
		# TRANS: present the output (stdout) to the user.
		Action.__init__(self, _("Filter through Command..."))
		self.post_result = True

	def get_description(self):
		return _("Run program and supply text on the standard input") + \
		        u" \N{GEAR}"

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

class BashCommand (Command):
	def __init__ (self, exepath, name):
		TextLeaf.__init__(self, exepath, name)

	def get_description (self):
		return unicode(self)

	def get_gicon (self):
		# not a file, so move on to get_icon_name
		pass

class CommandTextSource (TextSource):
	"""Yield path and command text items """
	def __init__(self):
		TextSource.__init__(self, name=_("Shell Commands"))

		# get bash aliases and functions
		bash_cmds = [u'shopt -s expand_aliases', u'source /etc/bash.bashrc']
		bashrc_path = u'%s/.bashrc' % (format(os.path.expanduser(u'~')),)
		bash_cmds.append(u' '.join((u'source', quote(bashrc_path))))
		self._bash_cmds = bash_cmds = u';'.join(bash_cmds) + '\n'

		# get alias names
		try:
			lines = check_output(('bash', '-c', bash_cmds + u'alias'))
		except OSError:
			# no bash
			pass
		else:
			# split into words
			self._aliases = aliases = []
			for word in shlex.split(lines):
				# ignore empty and 'alias'
				word = word.strip()
				if word and '=' in word:
					# reduce to name
					aliases.append(word[:word.find('=')])

		# get function names
		try:
			lines = check_output(('bash', '-c', bash_cmds + u'declare -F'))
		except OSError:
			# no bash
			pass
		else:
			self._fns = fns = []
			for line in lines.splitlines():
				words = shlex.split(line.strip())
				if words:
					# name is the last word in each line
					fn = words[-1]
					# probably don't want '_'-prefixed functions
					if not fn.startswith('_'):
						fns.append(fn)

	def get_rank(self):
		return 80

	def get_text_items(self, text):
		if not text.strip():
			return
		if '\n' in text:
			return
		## check for absolute path with arguments
		firstwords = text.split()
		## files are handled elsewhere
		if firstwords[0].startswith("/") and len(firstwords) == 1:
			return
		## absolute paths come out here since
		## os.path.join with two abspaths returns the latter
		firstword = firstwords[0]
		# bash aliases/functions: should supercede real commands (you might
		# have, say, alias ls='ls --color=auto')
		if (__kupfer_settings__["aliases"] and firstword in self._aliases) or \
		   (__kupfer_settings__["functions"] and firstword in self._fns):
			cmds = self._bash_cmds + u" ".join(firstwords)
			yield BashCommand(u'bash -c %s' % quote(cmds), text)
		# iterate over $PATH directories
		PATH = os.environ.get("PATH", os.defpath)
		for execdir in PATH.split(os.pathsep):
			exepath = os.path.join(execdir, firstword)
			# use filesystem encoding here
			exepath = gobject.filename_from_utf8(exepath)
			if os.access(exepath, os.R_OK|os.X_OK) and os.path.isfile(exepath):
				yield Command(exepath, text)
				break

	def get_description(self):
		return _("Run command-line programs")
