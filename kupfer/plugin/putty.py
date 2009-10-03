# -*- coding: utf8 -*-
from __future__ import with_statement

import os
import urllib

from kupfer.objects import Leaf, Action, Source
from kupfer.utils import spawn_async

__kupfer_name__ = _("PuTTY sessions")
__kupfer_sources__ = ("PuttySessionSource", )
__description__ = _("Session saved in PuTTY")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



class PuttySessionLeaf(Leaf):
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
		super(PuttyOpenSession, self).__init__(_('Open PuTTy session'))

	def activate(self, leaf):
		cli = ("putty", "-load", leaf.object)
		spawn_async(cli)

	def get_icon_name(self):
		return 'putty'



class PuttySessionSource(Source):
	''' indexes session saved in putty '''
	def __init__(self, name=_("PuTTy Session")):
		super(PuttySessionSource, self).__init__(name)
		self._putty_sessions_dir = os.path.expanduser('~/.putty/sessions')

	def is_dynamic(self):
		return True

	def get_items(self):
		for filename in os.listdir(self._putty_sessions_dir):
			if filename == 'Default%20Settings':
				continue

			obj_path = os.path.join(self._putty_sessions_dir, filename)
			if os.path.isfile(obj_path):
				name = urllib.unquote(filename)
				description = self._load_host_from_session_file(obj_path)
				yield PuttySessionLeaf(name, description)

	def get_description(self):
		return _("Session saved in Putty")

	def get_icon_name(self):
		return "putty"

	def provides(self):
		yield PuttySessionLeaf

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
		except Exception, err:
			print err

		else:
			return user + '@' + host if user else host

		return 'PuTTY session'




