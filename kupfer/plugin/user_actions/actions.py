# -*- coding: UTF-8 -*-
from __future__ import with_statement

__version__ = "2010-05-22"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import re
import ConfigParser

from kupfer import pretty
from kupfer import config
from kupfer import utils
from kupfer import kupferstring
from kupfer import commandexec
from kupfer.obj import objects
from kupfer.objects import OperationError, Action, Source


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

	def wants_context(self):
		return True

	def activate(self, leaf, ctx):
		argv = utils.argv_for_commandline(self.command)
		if '$s' in argv:
			argv[argv.index('$s')] = leaf.object
		if self.gather_result:
			acom = utils.AsyncCommand(argv, self.finish_callback, 15)
			acom.token = ctx
		else:
			try:
				if self.launch_in_terminal:
					utils.spawn_in_terminal(argv)
				else:
					utils.spawn_async_raise(argv)
			except utils.SpawnError as exc:
				raise OperationError(exc)

	def finish_callback(self, acommand, output, stderr):
		ctx = acommand.token
		out = kupferstring.fromlocale(output)
		if self.gather_result == 'url':
			objs = [objects.UrlLeaf(iout) for iout in out.split()]
		elif self.gather_result == 'file':
			objs = [objects.FileLeaf(iout) for iout in out.split()]
		elif self.gather_result == 'one-text':
			objs = (objects.TextLeaf(out), )
		else:
			objs = [objects.TextLeaf(iout) for iout in out.split()]
		if objs:
			if len(objs) == 1:
				ctx.register_late_result(objs[0])
			else:
				result = UserActionResultSource(objs)
				leaf = objects.SourceLeaf(result,
						_("%s Action Result") % self.name)
				ctx.register_late_result(leaf)

	def get_description(self):
		return self.description

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


def load_actions():
	"""docstring for load_actions"""
	config_file = config.get_config_file('user_actions.cfg')
	if not config_file:
		return
	cfgpars = ConfigParser.SafeConfigParser(_ACTION_DEFAULTS)
	cfgpars.read(config_file)
	for section in cfgpars.sections():
		command = cfgpars.get(section, 'command')
		if not command:
			pretty.print_info('missing command for action:', section)
			continue
		action = UserAction(section, command)
		leaf_types = cfgpars.get(section, 'objects')
		if leaf_types:
			leaf_types = [S.strip() for S in leaf_types.split(',')]
			action.leaf_types = leaf_types
		action.description = cfgpars.get(section, 'description')
		objects_filter = cfgpars.get(section, 'objects_filter')
		if objects_filter:
			action.objects_filter = [S.strip() for S
					in objects_filter.split(';')]
		launch_in_terminal = str(cfgpars.get(section, 'launch_in_terminal'))
		action.launch_in_terminal = (launch_in_terminal.strip().lower()
				in ('true', 'ok', 'yes', '1'))
		action.gather_result = cfgpars.get(section, 'gather_result')
		filters = cfgpars.get(section, 'filters')
		if filters:
			action.filters = [dict(fili.split('=', 1)
				for fili in filtr.split('&'))
				for filtr in filters.split('|')]
		yield action


def save_actions(actions):
	cfgpars = ConfigParser.SafeConfigParser()
	for action in actions:
		cfgpars.add_section(action.name)
		if action.leaf_types:
			cfgpars.set(action.name, 'objects', ','.join(action.leaf_types))
		cfgpars.set(action.name, 'command', action.command)
		cfgpars.set(action.name, 'description', action.description or '')
		if action.objects_filter:
			objects_filter = ';'.join(action.objects_filter)
			cfgpars.set(action.name, 'objects_filter', objects_filter)
		cfgpars.set(action.name, 'launch_in_terminal',
				str(action.launch_in_terminal))
		cfgpars.set(action.name, 'gather_result', action.gather_result or '')
		if action.filters:
			filters = '|'.join('&'.join(key + '=' + val for key, val
				in filtetitem.iteritems()) for filtetitem in action.filters)
			cfgpars.set(action.name, 'filters', filters)
	config_file = config.save_config_file('user_actions.cfg')
	with open(config_file, 'wb') as configfile:
		cfgpars.write(configfile)
