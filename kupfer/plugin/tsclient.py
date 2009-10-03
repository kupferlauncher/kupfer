# -*- coding: utf8 -*-
from __future__ import with_statement

import os

from kupfer.objects import Leaf, Action, Source
from kupfer.utils import spawn_async

__kupfer_name__ = _("Terminal Server Client")
__kupfer_sources__ = ("TsclientSessionSource", )
__description__ = _("Session saved in Terminam Server Client")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



class TsclientSessionLeaf(Leaf):
	""" Leaf represent session saved in Tsclient"""

	def __init__(self, obj_path, name, description):
		Leaf.__init__(self, obj_path, name)
		self._description = description

	def get_actions(self):
		yield TsclientOpenSession()

	def get_description(self):
		return self._description

	def get_icon_name(self):
		return "computer"



class TsclientOpenSession(Action):
	''' opens tsclient session '''
	def __init__(self):
		Action.__init__(self, _('Open Terminal Server Client session'))

	def activate(self, leaf):
		cli = ("tsclient", "-x", leaf.object)
		spawn_async(cli)

	def get_icon_name(self):
		return 'tsclient'



class TsclientSessionSource(Source):
	''' indexes session saved in tsclient '''
	def __init__(self, name=_("TSClient sessions")):
		Source.__init__(self, name)
		self._sessions_dir = os.path.expanduser('~/.tsclient')

	def is_dynamic(self):
		return False

	def get_items(self):
		for filename in os.listdir(self._sessions_dir):
			if not filename.endswith('.rdp'):
				continue

			obj_path = os.path.join(self._sessions_dir, filename)
			if os.path.isfile(obj_path):
				name = filename[:-4]
				description = self._load_descr_from_session_file(obj_path)
				yield TsclientSessionLeaf(obj_path, name, description)

	def get_description(self):
		return _("Session saved in Terminal Server Client")

	def get_icon_name(self):
		return "tsclient"

	def provides(self):
		yield TsclientSessionLeaf

	def _load_descr_from_session_file(self, filepath):
		user = None
		host = None
		try:
			with open(filepath, 'r') as session_file:
				for line in session_file:
					if line.startswith('full address:s:'):
						host = line.split(':s:', 2)[1].strip()
					elif line.startswith('username:s:'):
						user = line.split(':s:', 2)[1].strip()
		except Exception, err:
			print err

		else:
			return user + '@' + host if user else host

		return 'TSClient; session'




