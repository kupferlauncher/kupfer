# -*- coding: utf8 -*-
from __future__ import with_statement

import os
import urllib

from kupfer.objects import Leaf, Action, Source, TextSource, FilesystemWatchMixin
from kupfer import utils

__kupfer_name__ = _("PuTTY Sessions")
__kupfer_sources__ = ("PuttySessionSource", )
__description__ = _("Quick access to PuTTY Sessions")
__version__ = "0.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


class PuttySession(Leaf):
	""" Leaf represent session saved in PuTTy"""

	def __init__(self, name, description):
		Leaf.__init__(self, name, name)
		self._description = description

	def get_actions(self):
		yield PuttyOpenSession()

	def get_description(self):
		return self._description

	def get_icon_name(self):
		return "computer"


class PuttyOpenSession(Action):
	''' opens putty session '''
	def __init__(self):
		Action.__init__(self, _('Start PuTTY Session'))

	def activate(self, leaf):
		utils.launch_commandline("putty -load '%s'" % leaf.object)

	def get_icon_name(self):
		return 'putty'


class PuttySessionSource(Source, FilesystemWatchMixin):
	''' indexes session saved in putty '''
	def __init__(self, name=_("PuTTY Sessions")):
		super(PuttySessionSource, self).__init__(name)
		self._putty_sessions_dir = os.path.expanduser('~/.putty/sessions')
		self.unpickle_finish()

	def unpickle_finish(self):
		self.monitor_token = self.monitor_directories(self._putty_sessions_dir)

	def get_items(self):
		if not os.path.isdir(self._putty_sessions_dir):
			return

		for filename in os.listdir(self._putty_sessions_dir):
			if filename == 'Default%20Settings':
				continue

			obj_path = os.path.join(self._putty_sessions_dir, filename)
			if os.path.isfile(obj_path):
				name = urllib.unquote(filename)
				description = self._load_host_from_session_file(obj_path)
				yield PuttySession(name, description)

	def get_description(self):
		return _("Session saved in Putty")

	def get_icon_name(self):
		return "putty"

	def provides(self):
		yield PuttySession

	def _load_host_from_session_file(self, filepath):
		user = None
		host = None
		try:
			with open(filepath, 'r') as session_file:
				for line in session_file:
					if line.startswith('HostName='):
						host = line.split('=', 2)[1].strip()

					elif line.startswith('UserName='):
						user = line.split('=', 2)[1].strip()

		except IOError, err:
			self.output_error(err)

		else:
			if host:
				return unicode(user + '@' + host if user else host)

		return u'PuTTY Session'




