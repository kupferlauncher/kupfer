# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import utils

__kupfer_name__ = _("Terminal Server Client")
__kupfer_sources__ = ("TsclientSessionSource", )
__kupfer_contents__ = ("TsclientSessionSource", )
__description__ = _("Session saved in Terminal Server Client")
__version__ = "0.2"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



class TsclientSession(Leaf):
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
		Action.__init__(self, _('Start Terminal Server Session'))

	def activate(self, leaf):
		utils.launch_commandline("tsclient -x '%s'" % leaf.object)

	def get_icon_name(self):
		return 'tsclient'


class TsclientSessionSource(AppLeafContentMixin, Source, PicklingHelperMixin,
		FilesystemWatchMixin):
	''' indexes session saved in tsclient '''

	appleaf_content_id = 'tsclient'

	def __init__(self, name=_("TSClient sessions")):
		Source.__init__(self, name)
		self._sessions_dir = os.path.expanduser('~/.tsclient')
		self.unpickle_finish()

	def unpickle_finish(self):
		if not os.path.isdir(self._sessions_dir):
			return

		self.monitor_token = self.monitor_directories(self._sessions_dir)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename().endswith('.rdp')

	def get_items(self):
		if not os.path.isdir(self._sessions_dir):
			return

		for filename in os.listdir(self._sessions_dir):
			if not filename.endswith('.rdp'):
				continue

			obj_path = os.path.join(self._sessions_dir, filename)
			if os.path.isfile(obj_path):
				name = filename[:-4]
				description = self._load_descr_from_session_file(obj_path)
				yield TsclientSession(obj_path, name, description)

	def get_description(self):
		return _("Session saved in Terminal Server Client")

	def get_icon_name(self):
		return "tsclient"

	def provides(self):
		yield TsclientSession

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

		except IOError, err:
			self.output_error(err)

		else:
			if host:
				return unicode(user + '@' + host if user else host)

		return u'Terminal Server Client Session'




