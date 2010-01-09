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
			if action.requires_object():
				ret = action.activate(obj, iobj)
			else:
				ret = action.activate(obj)

		# remember last command, but not delegated commands.
		if not delegate:
			self.last_command = (obj, action, iobj)

		# Delegated command execution was previously requested: we take
		# the result of the nested execution context
		if self._delegate:
			res, ret = ret
			return self._return_result(res, ret)

		def valid_result(ret):
			return ret and (not hasattr(ret, "is_valid") or ret.is_valid())

		# handle actions returning "new contexts"
		res = RESULT_NONE
		if action.is_factory() and valid_result(ret):
			res = RESULT_SOURCE
		if action.has_result() and valid_result(ret):
			res = RESULT_OBJECT
		elif action.is_async():
			self.task_runner.add_task(ret)
			res = RESULT_ASYNC

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


