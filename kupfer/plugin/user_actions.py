# -*- coding: UTF-8 -*-
from __future__ import with_statement

__kupfer_name__ = _("User Actions")
__kupfer_action_generators__ = ("UserActionsGenerator", )
__description__ = _("User defined actions")
__version__ = "2010-04-21"
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

import re
import os.path
import subprocess
import ConfigParser

from kupfer import utils
from kupfer import config
from kupfer.obj.base import ActionGenerator, Action, Source
from kupfer.obj import objects


class UserAction(Action):
	def __init__(self, name, command):
		Action.__init__(self, name)
		self.command = command
		self.leaf_types = None
		self.description = None
		self.objects_filter = None
		self.launch_in_terminal = False
		self.gather_result = None
		self.filters = []

	def activate(self, leaf):
		cmd = self.command
		if '$s' in cmd:
			try:
				cmd = self.command.replace('$s', leaf.object)
			except TypeError:
				return
		if self.gather_result:
			proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
			out, _err = proc.communicate()
			if self.gather_result == 'url':
				objs = [objects.UrlLeaf(iout) for iout in out.split()]
			elif self.gather_result == 'file':
				objs = [objects.FileLeaf(iout) for iout in out.split()]
			elif self.gather_result == 'one-text':
				objs = (objects.TextLeaf(out), )
			else:
				objs = [objects.TextLeaf(iout) for iout in out.split()]
			return UserActionResultSource(objs)
		else:
			utils.launch_commandline(cmd, self.name, self.launch_in_terminal)

	def is_factory(self):
		return self.gather_result is not None

	def get_description(self):
		return self.description

	def set_filters(self, filters):
		if not filters:
			return
		self.objects_filter = [S.strip() for S in filters.split(';')]

	def is_valid_for_leaf(self, leaf):
		if self.leaf_types:
			if not self._check_leaf(leaf):
				return False
		if self.objects_filter:
			if not any(re.match(ifilter, leaf.object) for ifilter
					in self.objects_filter):
				return False
		if not self.filters:
			return True
		for filtr in self.filters:
			result = True
			for key, value in filtr.iteritems():
				result = result and getattr(leaf, key, None) == value
			if result:
				return True
		return False

	def _check_leaf(self, leaf):
		if isinstance(leaf, objects.FileLeaf):
			if leaf.is_dir():
				return 'dir' in self.leaf_types
			if leaf._is_executable() and 'executable' in self.leaf_types:
				return True
			return 'file' in self.leaf_types
		if isinstance(leaf, objects.UrlLeaf):
			return 'url' in self.leaf_types
		if isinstance(leaf, objects.TextLeaf):
			return 'text' in self.leaf_types
		# check class name
		leaf_class = leaf.__class__.__name__.split('.')[-1]
		return leaf_class in self.leaf_types


class UserActionResultSource(Source):
	def __init__(self, result):
		Source.__init__(self, name=_("User Action Result"))
		self.result = result

	def get_items(self):
		return self.result


_ACTION_DEFAULTS = {
		'command': None,
		'objects': None,
		'description': None,
		'objects_filter': None,
		'launch_in_terminal': False,
		'gather_result': None,
		'filters': None}


class UserActionsGenerator(ActionGenerator):
	def __init__(self):
		ActionGenerator.__init__(self)
		self._last_loaded_time = 0
		self._config_file = config.get_config_file('user_actions.cfg')
		self._actions = []
		self._load()

	def _load(self):
		if not self._config_file or not os.path.isfile(self._config_file):
			self.output_debug('no config file')
			return []

		config_file_mtime = os.path.getmtime(self._config_file)
		if self._last_loaded_time >= config_file_mtime:
			return self._actions

		self.output_debug('loading actions', self._config_file)

		self._last_loaded_time = config_file_mtime
		self._actions = []
		cfgpars = ConfigParser.SafeConfigParser(_ACTION_DEFAULTS)
		cfgpars.read(self._config_file)
		for section in cfgpars.sections():
			command = cfgpars.get(section, 'command')
			if not command:
				self.output_info('missing command for action:', section)
				continue
			action = UserAction(section, command)
			leaf_types = cfgpars.get(section, 'objects')
			if leaf_types:
				leaf_types = [S.strip() for S in leaf_types.split(',')]
				action.leaf_types = leaf_types
			action.description = cfgpars.get(section, 'description')
			action.set_filters(cfgpars.get(section, 'objects_filter'))
			action.launch_in_terminal = bool(cfgpars.get(section,
					'launch_in_terminal'))
			action.gather_result = cfgpars.get(section, 'gather_result')
			filters = cfgpars.get(section, 'filters')
			if filters:
				action.filters = [dict(fili.split('=', 1)
					for fili in filtr.split('&'))
					for filtr in filters.split('|')]
			self._actions.append(action)
		return self._actions

	def get_actions_for_leaf(self, leaf):
		for action in self._load():
			if action.is_valid_for_leaf(leaf):
				yield action

