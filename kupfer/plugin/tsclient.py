# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os

from kupfer.objects import Action, AppLeafContentMixin
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import utils, icons
from kupfer.obj.grouping import ToplevelGroupingSource 
from kupfer.obj.hosts import HOST_NAME_KEY, HostLeaf

__kupfer_name__ = _("Terminal Server Client")
__kupfer_sources__ = ("TsclientSessionSource", )
__kupfer_actions__ = ("TsclientOpenSession", )
__description__ = _("Session saved in Terminal Server Client")
__version__ = "2010-01-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



TSCLIENT_SESSION_KEY = "TSCLIENT_SESSION"

class TsclientSession(HostLeaf):
	""" Leaf represent session saved in Tsclient"""

	def __init__(self, obj_path, name, description):
		slots = {HOST_NAME_KEY: name, TSCLIENT_SESSION_KEY: obj_path}
		HostLeaf.__init__(self, slots, name)
		self._description = description

	def get_description(self):
		return self._description

	def get_gicon(self):
		return icons.ComposedIcon(HostLeaf.get_icon_name(self), "tsclient")


class TsclientOpenSession(Action):
	''' opens tsclient session '''
	def __init__(self):
		Action.__init__(self, _('Start Session'))

	def activate(self, leaf):
		session = leaf[TSCLIENT_SESSION_KEY]
		utils.launch_commandline("tsclient -x '%s'" % session)

	def get_icon_name(self):
		return 'tsclient'

	def item_types(self):
		yield HostLeaf

	def valid_for_item(self, item):
		return item.check_key(TSCLIENT_SESSION_KEY)


class TsclientSessionSource(AppLeafContentMixin, ToplevelGroupingSource,
		FilesystemWatchMixin, PicklingHelperMixin):
	''' indexes session saved in tsclient '''

	appleaf_content_id = 'tsclient'

	def __init__(self, name=_("TSClient sessions")):
		ToplevelGroupingSource.__init__(self, name, "hosts")
		self._sessions_dir = os.path.expanduser('~/.tsclient')
		self._version = 2

	def initialize(self):
		ToplevelGroupingSource.initialize(self)
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
		return _("Saved sessions in Terminal Server Client")

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
				return unicode(user + '@' + host if user else host, "UTF-8",
						"replace")

		return u'Terminal Server Client Session'




