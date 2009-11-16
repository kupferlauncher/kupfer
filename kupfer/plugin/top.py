# -*- coding: UTF-8 -*-

import os
import subprocess

from kupfer.objects import Action, Source, Leaf
from kupfer import utils
from kupfer import plugin_support

__kupfer_name__ = _("Top")
__kupfer_sources__ = ("TaskSource", )
__description__ = _("Show Running Task and allow to Send Signals to them.")
__version__ = "1.0"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


# FIXME: how to force no-top-level?
__kupfer_settings__ = plugin_support.PluginSettings(
	plugin_support.SETTING_PREFER_CATALOG,
)



class Task(Leaf):
	def __init__(self, path, name, description=None):
		Leaf.__init__(self, path, name)
		self._description = description

	def get_description(self):
		return self._description

	def get_actions(self):
		yield SendSignal()


class SendSignal(Action):
	def __init__(self):
		Action.__init__(self, _("Send Signal..."))

	def activate(self, leaf, iobj):
		os.kill(int(leaf.object), iobj.object)

	def requires_object(self):
		return True
	
	def object_types(self):
		yield _Signal

	def object_source(self, for_item=None):
		return _SignalsSource()


class _Signal(Leaf):
	def get_description(self):
		return "kill -%s ..." % self.object


_SIGNALS = [
		(14, "ALRM"),
		(1, "HUP"),
		(2, "INT"),
		(9, "KILL"),
		(13, "PIPE"),
		(15, "TERM"),
		("USR1", "USR1"),
		("USR2", "USR2"),
		(6, "ABRT"),
		(8, "FPE"),
		(4, "ILL"),
		(3, "QUIT"),
		(11, "SEGV"),
		(5, "TRAP"),
]


class _SignalsSource(Source):
	def __init__(self):
		Source.__init__(self, _("Signals"))

	def get_items(self):
		for sigid, signame in _SIGNALS:
			yield _Signal(sigid, signame)

	def provides(self):
		yield _Signal


class TaskSource(Source):
	def __init__(self, name=_("Running Tasks")):
		Source.__init__(self, name)

	def is_dynamic(self):
		return True

	def get_items(self):
		# tasks for current user
		uid = os.getuid()
		command = 'top -b -n 1 -u %d' % uid
		proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
		out, _err = proc.communicate()

		header_read = False
		for line in out.split('\n'):
			line = line.strip()
			if line == '':
				header_read = True
				continue

			if not header_read:
				continue

			(pid, user, pr, ni, virt, res, shr, s, cpu, mem, time, cmd) = \
					line.split(None, 11)
			if pid == 'PID':
				continue	# skip header

			description = (
					_("pid: %(pid)s  user: %(user)s  cpu: %(cpu)s%%   mem: %(mem)s   time: %(time)s") \
					% dict(pid=pid, user=user, cpu=cpu, mem=mem, time=time))
			yield Task(pid, cmd, description)


	def get_description(self):
		return _("Running Task for Current User")

	def get_icon_name(self):
		return "system"

	def provides(self):
		yield Task



