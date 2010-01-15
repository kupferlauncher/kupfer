from __future__ import with_statement

import contextlib

import gobject

from kupfer import task

RESULT_NONE, RESULT_OBJECT, RESULT_SOURCE, RESULT_ASYNC = (1, 2, 3, 4)
RESULTS_SYNC = (RESULT_OBJECT, RESULT_SOURCE)

_action_exec_context = None
def DefaultActionExecutionContext():
	global _action_exec_context
	if _action_exec_context is None:
		_action_exec_context = ActionExecutionContext()
	return _action_exec_context

class ActionExecutionError (Exception):
	pass

def activate_action(obj, action, iobj):
	""" Activate @action in simplest manner """
	if not _is_multiple(obj) and not _is_multiple(iobj):
		return _activate_action_single(obj, action, iobj)
	else:
		return _activate_action_multiple(obj, action, iobj)

def _activate_action_single(obj, action, iobj):
	if action.requires_object():
		ret = action.activate(obj, iobj)
	else:
		ret = action.activate(obj)
	return ret

def _activate_action_multiple(obj, action, iobj):
	if not hasattr(action, "activate_multiple"):
		ret = None
		iobjs = (None, ) if iobj is None else _get_leaf_members(iobj)
		for L in _get_leaf_members(obj):
			for I in iobjs:
				ret = _activate_action_single(L, action, I) or ret
		return ret

	if action.requires_object():
		ret = action.activate_multiple(_get_leaf_members(obj), _get_leaf_members(iobj))
	else:
		ret = action.activate_multiple(_get_leaf_members(obj))
	return ret

def parse_action_result(action, ret):
	"""Return result type for @action and return value @ret"""
	def valid_result(ret):
		return ret and (not hasattr(ret, "is_valid") or ret.is_valid())

	# handle actions returning "new contexts"
	res = RESULT_NONE
	if action.is_factory() and valid_result(ret):
		res = RESULT_SOURCE
	if action.has_result() and valid_result(ret):
		res = RESULT_OBJECT
	elif action.is_async():
		res = RESULT_ASYNC
	return res


class ActionExecutionContext (gobject.GObject):
	"""
	command-result (result_type, result)
		Emitted when a command is carried out, with its resulting value
	"""
	__gtype_name__ = "ActionExecutionContext"
	def __init__(self):
		gobject.GObject.__init__(self)
		self.task_runner = task.TaskRunner(end_on_finish=False)
		self._nest_level = 0
		self._delegate = False
		self.last_command = None

	def check_valid(self, obj, action, iobj):
		pass

	@contextlib.contextmanager
	def _nesting(self):
		try:
			self._nest_level += 1
			self._delegate = False
			yield
		finally:
			self._nest_level -= 1

	def _is_nested(self):
		return self._nest_level

	def run(self, obj, action, iobj, delegate=False):
		"""
		Activate the command (obj, action, iobj), where @iobj may be None

		Return a tuple (DESCRIPTION; RESULT)

		If a command carries out another command as part of its execution,
		and wishes to delegate to it, pass True for @delegate.
		"""
		if not action or not obj:
			raise ActionExecutionError("Primary Object and Action required")
		if iobj is None and action.requires_object():
			raise ActionExecutionError("%s requires indirect object" % action)

		with self._nesting():
			ret = activate_action(obj, action, iobj)

		# remember last command, but not delegated commands.
		if not delegate:
			self.last_command = (obj, action, iobj)

		# Delegated command execution was previously requested: we take
		# the result of the nested execution context
		if self._delegate:
			res, ret = ret
			return self._return_result(res, ret)

		res = parse_action_result(action, ret)
		if res == RESULT_ASYNC:
			self.task_runner.add_task(ret)

		# Delegated command execution was requested: we pass
		# through the result of the action to the parent execution context
		if delegate and self._is_nested():
			self._delegate = True
			return (res, ret)

		return self._return_result(res, ret)

	def _return_result(self, res, ret):
		if not self._is_nested():
			self.emit("command-result", res, ret)
		return res, ret

# Action result type, action result
gobject.signal_new("command-result", ActionExecutionContext,
		gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT))

def _is_multiple(leaf):
	return hasattr(leaf, "get_multiple_leaf_representation")

def _get_leaf_members(leaf):
	"""
	Return an iterator to members of @leaf, if it is a multiple leaf
	"""
	try:
		return leaf.get_multiple_leaf_representation()
	except AttributeError:
		return (leaf, )

def action_valid_for_item(action, leaf):
	return all(action.valid_for_item(L) for L in _get_leaf_members(leaf))

def actions_for_item(leaf, sourcecontroller):
	if leaf is None:
		return []
	actions = None
	for L in _get_leaf_members(leaf):
		l_actions = set(L.get_actions())
		l_actions.update(sourcecontroller.get_actions_for_leaf(L))
		if actions is None:
			actions = l_actions
		else:
			actions.intersection_update(l_actions)
	return actions

def iobject_source_for_action(action, for_item):
	for leaf in _get_leaf_members(for_item):
		return action.object_source(leaf)

def iobjects_valid_for_action(action, for_item):
	"""
	Return a filtering *function* that will let through
	those leaves that are good iobjects for @action and @for_item.
	"""
	def valid_object(leaf, for_item):
		_valid_object = action.valid_object
		for L in _get_leaf_members(leaf):
			for I in _get_leaf_members(for_item):
				if not _valid_object(L, for_item=I):
					return False
		return True

	types = tuple(action.object_types())
	def type_obj_check(iobjs):
		for i in iobjs:
			if (isinstance(i, types) and valid_object(i, for_item=for_item)):
				yield i
	def type_check(itms):
		for i in itms:
			if isinstance(i, types):
				yield i

	if hasattr(action, "valid_object"):
		return type_obj_check
	else:
		return type_check

