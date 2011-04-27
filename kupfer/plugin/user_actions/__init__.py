# -*- coding: UTF-8 -*-
from __future__ import with_statement

__kupfer_name__ = _("User Actions")
__kupfer_action_generators__ = ("UserActionsGenerator", )
__description__ = _("User defined actions")
__version__ = "2010-05-12"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


'''
Allow user to define own actions.
Example actions (defined in ~/.config/kupfer/user_actions.cfg'):

[Download with GWget]
objects=url,text
command=gwget $s

[Edit with GIMP]
objects=file
objects_filter=.*(jpg|png)$
command=gimp $s
description=Edit file with GIMP

[Compute MD5sum]
objects=file
command=md5sum $s
gather_result=one-text

[Run by Sudo]
objects=executable
command=gksudo $s


Fields:
	section: action name
	object: name of leaf type (file, text, url, executable, dir)
	objects_filter: optional regex that allow to show action only for selected
		leaves
	command: command do execute; $s is replaces by leaf.object
	description: optional description for the action
	launch_in_terminal: optional, if set launch command in terminal
	gather_result: optional, get result as text|url|file|one-text; default: text
	filters: expression that define what attributes must have leaf to be
		assigned to action. Expression contains parts separated by '|'.
		Each part contains pair of <attribute name>=<value>, separated by '&'.
		Example: filters=source_name=foo&object=12|source_name=bar
		- action is available for object that have source_name = foo and
		  object = 12 or objects that have source_name = bar
'''

import os.path

from kupfer import config
from kupfer import plugin_support
from kupfer import pretty
from kupfer.obj.base import ActionGenerator

from .configuration import PluginSettings
from .actions import UserAction
from . import actions


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		'key': 'actions',
		'label': 'Configure actions',
		'type': PluginSettings,
		'value': None,
	},
)


class UserActionsGenerator(ActionGenerator, pretty.OutputMixin):
	def __init__(self):
		ActionGenerator.__init__(self)
		self._last_loaded_time = 0
		self._actions = []
		self._load()

	def _load(self):
		config_file = config.get_config_file('user_actions.cfg')
		if not config_file:
			self.output_debug('no config file')
			return []
		config_file_mtime = os.path.getmtime(config_file)
		if self._last_loaded_time >= config_file_mtime:
			return self._actions
		self.output_debug('loading actions', config_file)
		self._last_loaded_time = config_file_mtime
		self._actions = list(actions.load_actions())
		return self._actions

	def get_actions_for_leaf(self, leaf):
		for action in self._load():
			if action.is_valid_for_leaf(leaf):
				yield action
