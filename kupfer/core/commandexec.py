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


import collections
import contextlib
import itertools
import sys

from gi.repository import GObject

from kupfer import pretty
from kupfer import task
from kupfer import uiutils
from kupfer.objects import OperationError
from kupfer.obj.base import Leaf, Source
from kupfer.obj.objects import SourceLeaf
from kupfer.obj.sources import MultiSource
from kupfer.obj.compose import MultipleLeaf

RESULT_NONE, RESULT_OBJECT, RESULT_SOURCE, RESULT_ASYNC = (1, 2, 3, 4)
RESULTS_SYNC = (RESULT_OBJECT, RESULT_SOURCE)

_MAX_LAST_RESULTS = 10

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

def _wants_context(action):
    return action.wants_context()

def activate_action(context, obj, action, iobj):
    """ Activate @action in simplest manner """
    kwargs = {}
    if _wants_context(action):
        kwargs['ctx'] = context
    if not _is_multiple(obj) and not _is_multiple(iobj):
        return _activate_action_single(obj, action, iobj, kwargs)
    else:
        return _activate_action_multiple(obj, action, iobj, kwargs)

def _activate_action_single(obj, action, iobj, kwargs):
    if action.requires_object():
        ret = action.activate(obj, iobj, **kwargs)
    else:
        ret = action.activate(obj, **kwargs)
    return ret

def _activate_action_multiple(obj, action, iobj, kwargs):
    if not hasattr(action, "activate_multiple"):
        iobjs = (None, ) if iobj is None else _get_leaf_members(iobj)
        return _activate_action_multiple_multiplied(_get_leaf_members(obj),
                action, iobjs, kwargs)

    if action.requires_object():
        ret = action.activate_multiple(_get_leaf_members(obj),
                _get_leaf_members(iobj), **kwargs)
    else:
        ret = action.activate_multiple(_get_leaf_members(obj), **kwargs)
    return ret

def _activate_action_multiple_multiplied(objs, action, iobjs, kwargs):
    """
    Multiple dispatch by "mulitplied" invocation of the simple activation

    Return an iterable of the return values.
    """
    rets = []
    for L in objs:
        for I in iobjs:
            ret = _activate_action_single(L, action, I, kwargs)
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

def parse_late_action_result(action, ret):
    # Late result is assumed to be a Leaf (Object) result
    # by default for backward compat.
    #
    # It is also allowed to be a Source
    def valid_result(ret):
        return ret and (not hasattr(ret, "is_valid") or ret.is_valid())

    res = RESULT_NONE
    if isinstance(ret, Source) and valid_result(ret):
        res = RESULT_SOURCE
    elif valid_result(ret):
        res = RESULT_OBJECT
    return res

class ExecutionToken (object):
    """
    A token object that an ``Action`` carries with it
    from ``activate``.

    Must be used for access to current execution context,
    and to access the environment.
    """
    def __init__(self, aectx, async_token, ui_ctx):
        self._aectx = aectx
        self._token = async_token
        self._ui_ctx = ui_ctx

    def register_late_result(self, result_object, show=True):
        self._aectx.register_late_result(self._token, result_object, show=show,
                                         ctxenv=self._ui_ctx)

    def register_late_error(self, exc_info=None):
        self._aectx.register_late_error(self._token, exc_info)

    def delegated_run(self, *objs):
        return self._aectx.run(*objs, delegate=True, ui_ctx=self._ui_ctx)

    @property
    def environment(self):
        """This is a property for the current environment,
        acess env variables like this::

            ctx.environment.get_timestamp()

        Raises RuntimeError when not available.
        """
        if self._ui_ctx is not None:
            return self._ui_ctx
        else:
            raise RuntimeError("Environment Context not available")

class ActionExecutionContext (GObject.GObject, pretty.OutputMixin):
    """
    command-result (result_type, result)
        Emitted when a command is carried out, with its resulting value
    """
    __gtype_name__ = "ActionExecutionContext"
    def __init__(self):
        GObject.GObject.__init__(self)
        self.task_runner = task.TaskRunner(end_on_finish=False)
        self._nest_level = 0
        self._delegate = False
        self._command_counter = itertools.count()
        self.last_command_id = -1
        self.last_command = None
        self.last_executed_command = None
        self.last_results = collections.deque([], _MAX_LAST_RESULTS)

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
            self._do_error_conversion(cmdtuple, sys.exc_info())

    def _do_error_conversion(self, cmdtuple, exc_info):
        if not self.operation_error(exc_info, cmdtuple):
            raise
        etype, value, tb = exc_info
        raise ActionExecutionError(value).with_traceback(tb)

    def get_async_token(self):
        """Get an action execution for current execution

        Return a token for the currently active command execution.
        The token must be used for posting late results or late errors.
        """
        return (self.last_command_id, self.last_executed_command)

    def make_execution_token(self, ui_ctx):
        """
        Return an ExecutionToken for @self and @ui_ctx
        """
        return ExecutionToken(self, self.get_async_token(), ui_ctx)

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
                str(value), icon_name="kupfer")

    def register_late_error(self, token, exc_info=None):
        "Register an error in exc_info. The error must be an OperationError"
        if exc_info is None:
            exc_info = sys.exc_info()
        if isinstance(exc_info, Exception):
            exc_info = (type(exc_info), exc_info, None)
        command_id, cmdtuple = token
        self._do_error_conversion(cmdtuple, exc_info)

    def register_late_result(self, token, result, show=True, ctxenv=None):
        """Register a late result

        Result must be a Leaf (as in result object, not factory or async)

        If @show, possibly display the result to the user.
        """
        self.output_debug("Late result", repr(result), "for", token)
        command_id, (_ign1, action, _ign2) = token
        if result is None:
            raise ActionExecutionError("Late result from %s was None" % action)
        assert isinstance(result, (Leaf, Source))
        res_name = str(result)
        res_desc = result.get_description()
        if res_desc:
            description = "%s (%s)" % (res_name, res_desc)
        else:
            description = res_name

        # If only registration was requsted, remove the command id info
        if not show:
            command_id = -1

        result_type = parse_late_action_result(action, result)

        self.output_debug("late-command-result", command_id, result_type, result, ctxenv)

        if result_type == RESULT_NONE:
            return
        uiutils.show_notification(_('"%s" produced a result') % action, description)

        self.emit("late-command-result", command_id, result_type, result, ctxenv)
        self._append_result(result_type, result)

    def _append_result(self, res_type, result):
        if res_type == RESULT_OBJECT:
            self.last_results.append(result)

    def run(self, obj, action, iobj, delegate=False, ui_ctx=None):
        """
        Activate the command (obj, action, iobj), where @iobj may be None

        Return a tuple (DESCRIPTION; RESULT)

        If a command carries out another command as part of its execution,
        and wishes to delegate to it, pass True for @delegate.
        """
        self.last_command_id = next(self._command_counter)
        self.last_executed_command = (obj, action, iobj)

        if not action or not obj:
            raise ActionExecutionError("Primary Object and Action required")
        if iobj is None and action.requires_object():
            raise ActionExecutionError("%s requires indirect object" % action)
        self.output_debug(repr(obj), repr(action), repr(iobj), repr(ui_ctx))

        # The execution token object for the current invocation
        execution_token = self.make_execution_token(ui_ctx)
        with self._error_conversion(obj, action, iobj):
            with self._nesting():
                ret = activate_action(execution_token, obj, action, iobj)

        # remember last command, but not delegated commands.
        if not delegate:
            self.last_command = self.last_executed_command

        # Delegated command execution was previously requested: we take
        # the result of the nested execution context
        if self._delegate:
            res, ret = ret
            return self._return_result(res, ret, ui_ctx)

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

        return self._return_result(res, ret, ui_ctx)

    def _return_result(self, res, ret, ui_ctx):
        if not self._is_nested():
            self._append_result(res, ret)
            self.emit("command-result", res, ret, ui_ctx)
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
                for task_ in values:
                    self.output_debug("Registering async task", task_)
                    self.task_runner.add_task(task_)
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
                key, values = list(resmap.items())[0]
                return key, _make_retvalue(key, values)
            elif len(resmap) > 1:
                # Put the source in a leaf and return a multiple leaf
                source = _make_retvalue(RESULT_SOURCE, resmap[RESULT_SOURCE])
                objects = resmap[RESULT_OBJECT]
                objects.append(SourceLeaf(source))
                return RESULT_OBJECT, _make_retvalue(RESULT_OBJECT, objects)
            return RESULT_NONE, None


# Signature: Action result type, action result, gui_context
GObject.signal_new("command-result", ActionExecutionContext,
        GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN,
        (GObject.TYPE_INT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))

# Signature: Command ID, Action result type, action result, gui_context
GObject.signal_new("late-command-result", ActionExecutionContext,
        GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN,
        (GObject.TYPE_INT, GObject.TYPE_INT,
            GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
