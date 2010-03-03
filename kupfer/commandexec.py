"""
The main logic for executing constructed commands.

A command is normally a tuple of (object, action, indirect object).
Where, of course, the indirect object is often not needed (in this module we
then pass None in its stead).

This code was once a shining machine; While adding the "comma trick" and
support for "multiple dispatch" was easy in the rest of the program, it shed
its casualties here: While the main process is simple, we deal here with all
the exceptions that are, at the moment, tacked on.

The ActionExecutionContext (ACE) keeps track of its nested invocation, so that
we can catch the results of commands executed inside other commands. The
delegation mechanism allows a user of the ACE to indicate that the result of
the command should be passed on from the earlier (more nested) invocation.

Multiple dispatch is straightforward if the action implements the multiple
dispatch protocol. Is the protocol not implemented, the command is simply
"multiplied out": executed once for each object, or once for each combination
of object and indirect object.

With multiple command execution (and delegation), we must then process and
merge multiple return values.
"""
from __future__ import with_statement

import contextlib
import sys

import gobject

from kupfer import pretty
from kupfer import task
from kupfer import uiutils
from kupfer.objects import OperationError
from kupfer.obj.objects import SourceLeaf
from kupfer.obj.sources import MultiSource
from kupfer.obj.compose import MultipleLeaf

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

def _get_leaf_members(leaf):
	"""
	Return an iterator to members of @leaf, if it is a multiple leaf
	"""
	# NOTE : This function duplicates one in core/actionlogic.py
	try:
		return leaf.get_multiple_leaf_representation()
	except AttributeError:
		return (leaf, )

def _is_multiple(leaf):
	return hasattr(leaf, "get_multiple_leaf_representation")

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
		iobjs = (None, ) if iobj is None else _get_leaf_members(iobj)
		return _activate_action_multiple_multiplied(_get_leaf_members(obj),
				action, iobjs)

	if action.requires_object():
		ret = action.activate_multiple(_get_leaf_members(obj), _get_leaf_members(iobj))
	else:
		ret = action.activate_multiple(_get_leaf_members(obj))
	return ret

def _activate_action_multiple_multiplied(objs, action, iobjs):
	"""
	Multiple dispatch by "mulitplied" invocation of the simple activation

	Return an iterable of the return values.
	"""
	rets = []
	for L in objs:
		for I in iobjs:
			ret = _activate_action_single(L, action, I)
			rets.append(ret)
	ctx = DefaultActionExecutionContext()
	ret = ctx._combine_action_result_multiple(action, rets)
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
	elif action.is_async() and valid_result(ret):
		res = RESULT_ASYNC
	return res


class ActionExecutionContext (gobject.GObject, pretty.OutputMixin):
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

	@contextlib.contextmanager
	def _error_conversion(self, *cmdtuple):
		try:
			yield
		except OperationError:
			if not self.operation_error(sys.exc_info(), cmdtuple):
				raise
			etype, value, tb = sys.exc_info()
			raise ActionExecutionError, value, tb

	def operation_error(self, exc_info, cmdtuple):
		"Error when executing action. Return True when error was handled"
		if self._is_nested():
			return
		etype, value, tb = exc_info
		obj, action, iobj = cmdtuple
		# TRANS: When an error occurs in an action to be carried out,
		# TRANS: then this is the heading of the error notification
		return uiutils.show_notification(
				_("Could not to carry out '%s'") % action,
				unicode(value))

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

		with self._error_conversion(obj, action, iobj):
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
			# Register the task then "clear" the result
			self.output_debug("Registering async task", ret)
			self.task_runner.add_task(ret)
			res, ret = RESULT_NONE, None

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


	def _combine_action_result_multiple(self, action, retvals):
		self.output_debug("Combining", repr(action), retvals,
				"delegate=%s" % self._delegate)

		def _make_retvalue(res, values):
			"Construct a return value for type res"
			if res == RESULT_SOURCE:
				return values[0] if len(values) == 1 else MultiSource(values)
			if res == RESULT_OBJECT:
				return values[0] if len(values) == 1 else MultipleLeaf(values)
			if res == RESULT_ASYNC:
				# Register all tasks now, and return None upwards
				for task in values:
					self.output_debug("Registering async task", task)
					self.task_runner.add_task(task)
			return None

		if not self._delegate:
			values = []
			res = RESULT_NONE
			for ret in retvals:
				res_type = parse_action_result(action, ret)
				if res_type != RESULT_NONE:
					values.append(ret)
					res = res_type
			return _make_retvalue(res, values)
		else:
			# Re-parse result values
			res = RESULT_NONE
			resmap = {}
			for ret in retvals:
				if ret is None:
					continue
				res_type, ret_obj = ret
				if res_type != RESULT_NONE:
					res = res_type
					resmap.setdefault(res_type, []).append(ret_obj)

			# register tasks
			tasks = resmap.pop(RESULT_ASYNC, [])
			_make_retvalue(RESULT_ASYNC, tasks)

			if len(resmap) == 1:
				# Return the only of the Source or Object case
				key, values = resmap.items()[0]
				return key, _make_retvalue(key, values)
			elif len(resmap) > 1:
				# Put the source in a leaf and return a multiple leaf
				source = _make_retvalue(RESULT_SOURCE, resmap[RESULT_SOURCE])
				objects = resmap[RESULT_OBJECT]
				objects.append(SourceLeaf(source))
				return RESULT_OBJECT, _make_retvalue(RESULT_OBJECT, objects)
			return RESULT_NONE, None


# Action result type, action result
gobject.signal_new("command-result", ActionExecutionContext,
		gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT))

