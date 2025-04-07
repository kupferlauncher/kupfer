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

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.

TODO: delegation, run, combine_action_result_multiple need rethink / rebuild.
It's work quite well but is too complicated.
"""

from __future__ import annotations

import collections
import contextlib
import itertools
import sys
import typing as ty
from enum import IntEnum
from functools import partial

from gi.repository import GObject

from kupfer.core._support import get_leaf_members, is_multiple_leaf
from kupfer.obj import (
    Action,
    KupferObject,
    Leaf,
    OperationError,
    Source,
    SourceLeaf,
)
from kupfer.obj.compose import MultipleLeaf
from kupfer.obj.sources import MultiSource
from kupfer.support import pretty, task
from kupfer.ui import uiutils

if ty.TYPE_CHECKING:
    from gettext import gettext as _

    from kupfer.support.types import ExecInfo
    from kupfer.ui.uievents import GUIEnvironmentContext

__all__ = (
    "ActionExecutionContext",
    "ActionExecutionError",
    "ExecResult",
    "ExecutionToken",
    "default_action_execution_context",
)


class ExecResult(IntEnum):
    ZERO = 0  # when delegate
    NONE = 1
    OBJECT = 2
    SOURCE = 3
    ASYNC = 4
    REFRESH = 5

    @property
    def is_sync(self):
        return self in (ExecResult.OBJECT, ExecResult.SOURCE)


_MAX_LAST_RESULTS: ty.Final = 10

## CmdTuple keep information about command arguments (leaf, action and optional
## iobj)
CmdTuple = tuple[Leaf, Action, ty.Optional[Leaf]]

## Token keep information about (command id, and optional CmdTuple)
Token = tuple[int, ty.Optional[CmdTuple]]

## ActionResult is result (content) of action
ActionResult = ty.Union[Source, Leaf, task.Task, None]


# ActionResultRefresh is special leaf used as result of action that
# want refresh current leaves list.
ActionResultRefresh = Leaf(None, "ActionResultRefresh")


class ActionExecutionError(Exception):
    pass


class ExecutionToken:
    """A token object that an `Action` carries with it from `activate`.

    Must be used for access to current execution context, and to access the
    environment.
    """

    def __init__(
        self,
        aectx: ActionExecutionContext,
        async_token: Token,
        ui_ctx: GUIEnvironmentContext | None,
    ) -> None:
        """Initialize `ExecutionToken`.
        `aectx` is context of execution.
        `async_token` keeps data returned with late result
        `ui_ctx` is optional gui context
        """
        self._aectx: ActionExecutionContext = aectx
        self._token = async_token
        self._ui_ctx = ui_ctx

    def register_late_result(
        self, result_object: KupferObject, show: bool = True
    ) -> None:
        """Put execution result (`result_object`) into action execution
        context.
        If `show` it True - try to show result to the user.
        """
        self._aectx.register_late_result(
            self._token, result_object, show=show, ctxenv=self._ui_ctx
        )

    def register_late_error(
        self, exc_info: ExecInfo | BaseException | None = None
    ) -> None:
        """Put error (`exc_info`) from failed execution into action execution
        context."""
        self._aectx.register_late_error(self._token, exc_info)

    def delegated_run(
        self, obj: Leaf, action: Action, iobj: Leaf | None
    ) -> tuple[ExecResult, ty.Any]:
        """Activate action execution context - run it for `obj`, `action` and
        `iobj`."""
        return self._aectx.run(
            obj, action, iobj, delegate=True, ui_ctx=self._ui_ctx
        )

    @property
    def environment(self) -> GUIEnvironmentContext:
        """This is a property for the current environment,
        access env variables like this::

            ctx.environment.get_timestamp()

        Raises RuntimeError when not available.
        """
        if self._ui_ctx is not None:
            return self._ui_ctx

        raise RuntimeError("Environment Context not available")


class ActionExecutionContext(GObject.GObject, pretty.OutputMixin):  # type: ignore
    """The ActionExecutionContext (ACE) keeps track of its nested invocation,
    so that we can catch the results of commands executed inside other commands.
    The delegation mechanism allows a user of the ACE to indicate that the result
    of the command should be passed on from the earlier (more nested) invocation.

    ActionExecutionContext is singleton; to get it use
    `ActionExecutionContext.instance()` or `default_action_execution_context()`.

    command-result (result_type, result)
        Emitted when a command is carried out, with its resulting value
    """

    __gtype_name__ = "ActionExecutionContext"
    _instance: ActionExecutionContext | None = None

    @classmethod
    def instance(cls) -> ActionExecutionContext:
        if cls._instance is None:
            cls._instance = ActionExecutionContext()

        assert cls._instance
        return cls._instance

    def __init__(self) -> None:
        GObject.GObject.__init__(self)
        self._task_runner = task.TaskRunner(end_on_finish=False)
        self._nest_level = 0
        self._delegate = False
        self._command_counter = itertools.count()
        self.last_command_id = -1
        self.last_command: CmdTuple | None = None
        self._last_executed_command: CmdTuple | None = None
        self.last_results: collections.deque[ty.Any] = collections.deque(
            [], _MAX_LAST_RESULTS
        )

    @contextlib.contextmanager
    def _nesting(self):
        try:
            self._nest_level += 1
            self._delegate = False
            yield
        finally:
            self._nest_level -= 1

    @property
    def _is_nested(self) -> bool:
        return bool(self._nest_level)

    @contextlib.contextmanager
    def _error_conversion(self, cmdtuple: CmdTuple) -> ty.Any:
        try:
            yield
        except OperationError:
            self._do_error_conversion(cmdtuple, sys.exc_info())

    def _do_error_conversion(
        self, cmdtuple: CmdTuple, exc_info: ExecInfo
    ) -> None:
        if not self._operation_error(exc_info, cmdtuple):
            raise exc_info[1]  # type: ignore

        _etype, value, traceback = exc_info
        raise ActionExecutionError(value).with_traceback(traceback)

    def _get_async_token(self) -> Token:
        """Get an action execution for current execution

        Return a token for the currently active command execution.
        The token must be used for posting late results or late errors.
        """
        assert self.last_command_id is not None
        return (self.last_command_id, self._last_executed_command)

    def make_execution_token(
        self, ui_ctx: GUIEnvironmentContext | None
    ) -> ExecutionToken:
        """Return an ExecutionToken for @self and @ui_ctx."""
        return ExecutionToken(self, self._get_async_token(), ui_ctx)

    def _operation_error(
        self, exc_info: ExecInfo, cmdtuple: CmdTuple
    ) -> int | None:
        """Error when executing action - show notification to the user.
        Nested error are ignored."""

        if self._is_nested:
            return None

        _etype, value, _tb = exc_info
        _obj, action, _iobj = cmdtuple
        # TRANS: When an error occurs in an action to be carried out,
        # TRANS: then this is the heading of the error notification
        return uiutils.show_notification(
            _("Could not to carry out '%s'") % action,
            str(value),
            icon_name="kupfer",
        )

    def register_late_error(
        self, token: Token, exc_info: ExecInfo | BaseException | None = None
    ) -> None:
        """Register an error in exc_info. The error must be an OperationError.
        ActionExecutionError is raised.
        """
        if exc_info is None:
            exc_info = sys.exc_info()
        elif isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, None)

        _command_id, cmdtuple = token
        assert exc_info
        assert cmdtuple
        self._do_error_conversion(cmdtuple, exc_info)

    def register_late_result(
        self,
        token: Token,
        result: ty.Any,
        show: bool = True,
        ctxenv: GUIEnvironmentContext | None = None,
    ) -> None:
        """Register a late result.

        Result must be a Leaf (as in result object, not factory or async).

        If `show`, possibly display the result to the user (show leaf).
        Desktop notification is always displayed when there is any result.
        """
        self.output_debug("Late result", result, "for", token)
        assert token and token[1]
        command_id, (_ign1, action, _ign2) = token  # type: ignore
        if result is None:
            raise ActionExecutionError(f"Late result from {action} was None")

        assert isinstance(result, (Leaf, Source))
        description = res_name = str(result)
        if res_desc := result.get_description():
            description = f"{res_name} ({res_desc})"

        # If only registration was requested, remove the command id info
        if not show:
            command_id = -1

        result_type = _parse_late_action_result(action, result)

        self.output_debug(
            "late-command-result", command_id, result_type, result, ctxenv
        )

        if result_type == ExecResult.NONE:
            return

        if result_type != ExecResult.REFRESH:
            uiutils.show_notification(
                _('"%s" produced a result') % action, description
            )

        self.emit(
            "late-command-result", command_id, result_type, result, ctxenv
        )
        self._append_result(result_type, result)

    def _append_result(self, res_type: int, result: ty.Any) -> None:
        if res_type == ExecResult.OBJECT:
            self.last_results.append(result)

    def run(
        self,
        obj: Leaf,
        action: Action,
        iobj: Leaf | None,
        delegate: bool = False,
        ui_ctx: GUIEnvironmentContext | None = None,
    ) -> tuple[ExecResult, ty.Any]:
        """
        Activate the command (obj, action, iobj), where @iobj may be None

        Return a tuple (DESCRIPTION; RESULT)

        If a command carries out another command as part of its execution,
        and wishes to delegate to it, pass True for @delegate.
        """
        self.last_command_id = next(self._command_counter)
        self._last_executed_command = (obj, action, iobj)

        if not action or not obj:
            raise ActionExecutionError("Primary Object and Action required")

        if iobj is None and action.requires_object():
            raise ActionExecutionError(f"{action} requires indirect object")

        self.output_debug(obj, action, iobj, ui_ctx)

        # The execution token object for the current invocation
        execution_token = self.make_execution_token(ui_ctx)
        with self._error_conversion((obj, action, iobj)), self._nesting():
            ret = activate_action(execution_token, obj, action, iobj)

        # remember last command, but not delegated commands.
        if not delegate:
            self.last_command = self._last_executed_command

        # Delegated command execution was previously requested: we take
        # the result of the nested execution context
        if self._delegate:
            assert not ret or isinstance(ret, tuple)
            res, ret = ty.cast("tuple[ExecResult, ty.Any]", ret)
            return self._return_result(res, ret, ui_ctx)

        assert not ret or isinstance(ret, (Source, Leaf, task.Task))
        res = parse_action_result(action, ret)
        if res == ExecResult.ASYNC:
            # Register the task then "clear" the result
            self.output_debug("Registering async task", ret)
            assert isinstance(ret, task.Task)
            self._task_runner.add_task(ret)
            res, ret = ExecResult.NONE, None

        # Delegated command execution was requested: we pass
        # through the result of the action to the parent execution context
        if delegate and self._is_nested:
            self._delegate = True

        return self._return_result(res, ret, ui_ctx)

    def _return_result(
        self,
        res: ExecResult,
        ret: ty.Any,
        ui_ctx: GUIEnvironmentContext | None,
    ) -> tuple[ExecResult, ty.Any]:
        if not self._is_nested:
            self._append_result(res, ret)
            self.emit("command-result", res, ret, ui_ctx)

        return res, ret

    def combine_action_result_multiple(
        self,
        action: Action,
        retvals: ty.Iterable[tuple[ExecResult, ActionResult] | ActionResult],
    ) -> tuple[ExecResult, ActionResult] | ActionResult:
        """
        When delegate is False `retvals` is list of `ActionResult` and function
        return  `ActionResult`.

        When delegate it True  `retvals` is list of (ExecResult, ActionResult)
        and function return (ExecResult, ActionResult)

        """
        self.output_debug(
            "Combining", action, retvals, f"delegate={self._delegate}"
        )

        retvals_not_empty = filter(None, retvals)

        if self._delegate:
            return self._combine_action_result_multiple_delegate(
                action,
                ty.cast(
                    "list[tuple[ExecResult, ActionResult]]", retvals_not_empty
                ),
            )

        return self._combine_action_result_multiple_non_delegate(
            action, ty.cast("list[ActionResult]", retvals_not_empty)
        )

    def _combine_action_result_multiple_non_delegate(
        self,
        action: Action,
        retvals: ty.Iterable[ActionResult],
    ) -> ActionResult:
        values: list[ActionResult] = []
        res = ExecResult.NONE
        for ret in retvals:
            res_type = parse_action_result(action, ret)
            if res_type != ExecResult.NONE:
                values.append(ret)
                res = res_type

        return self._make_retvalue(res, values)

    def _combine_action_result_multiple_delegate(
        self,
        action: Action,
        retvals: list[tuple[ExecResult, ActionResult]],
    ) -> tuple[ExecResult, ActionResult]:
        # Re-parse result values
        resmap: dict[ExecResult, list[ActionResult]] = collections.defaultdict(
            list
        )
        for res_type, ret_obj in retvals:
            if res_type != ExecResult.NONE:
                resmap[res_type].append(ret_obj)

        # register tasks
        if tasks := resmap.pop(ExecResult.ASYNC, None):
            self._make_retvalue(ExecResult.ASYNC, tasks)

        if len(resmap) == 1:
            # Return the only of the Source or Object case
            key, values = resmap.popitem()
            return key, self._make_retvalue(key, values)

        if len(resmap) > 1:
            # Put the source in a leaf and return a multiple leaf
            source = self._make_retvalue(
                ExecResult.SOURCE, resmap[ExecResult.SOURCE]
            )
            assert isinstance(source, Source)
            objects = resmap[ExecResult.OBJECT]
            objects.append(SourceLeaf(source))
            return ExecResult.OBJECT, self._make_retvalue(
                ExecResult.OBJECT, objects
            )

        return ExecResult.NONE, None

    def _make_retvalue(
        self, res: ExecResult, values: list[ActionResult]
    ) -> ActionResult:
        """Construct a return value for type res.

        If Result is source or object construct MultpileSource/MultipleLeaf for
        many results or simple return first result.
        For async result register async task.
        """
        if res == ExecResult.SOURCE:
            return (
                values[0]
                if len(values) == 1
                else MultiSource(ty.cast("ty.Collection[Source]", values))
            )

        if res == ExecResult.OBJECT:
            return values[0] if len(values) == 1 else MultipleLeaf(values)

        if res == ExecResult.ASYNC:
            # Register all tasks now, and return None upwards
            for task_ in values:
                assert isinstance(task_, task.Task)
                self.output_debug("Registering async task", task_)
                self._task_runner.add_task(task_)

        return None


# Signature: Action result type, action result, gui_context
GObject.signal_new(
    "command-result",
    ActionExecutionContext,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (GObject.TYPE_INT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT),
)

# Signature: Command ID, Action result type, action result, gui_context
GObject.signal_new(
    "late-command-result",
    ActionExecutionContext,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (
        GObject.TYPE_INT,
        GObject.TYPE_INT,
        GObject.TYPE_PYOBJECT,
        GObject.TYPE_PYOBJECT,
    ),
)


## Get ActionExecutionContext instance
default_action_execution_context = ActionExecutionContext.instance


# pylint: disable=too-few-public-methods
@ty.runtime_checkable
class ActionActivateFunc(ty.Protocol):
    def __call__(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: ExecutionToken | None = None,
    ) -> ActionResult: ...


# pylint: disable=too-few-public-methods
@ty.runtime_checkable
class ActionActivateMultipleFunc(ty.Protocol):
    def __call__(
        self,
        leaf: ty.Iterable[Leaf],
        iobj: ty.Iterable[Leaf | None] | None = None,
        ctx: ExecutionToken | None = None,
    ) -> ActionResult: ...


def activate_action(
    context: ExecutionToken | None,
    obj: Leaf,
    action: Action,
    iobj: Leaf | None,
) -> tuple[ExecResult, ActionResult] | ActionResult:
    """Activate @action in simplest manner"""

    if not action.wants_context():
        context = None

    if not is_multiple_leaf(obj) and not is_multiple_leaf(iobj):
        return _activate_action_single(obj, action, iobj, context)

    return _activate_action_multiple(obj, action, iobj, context)


def _activate_action_single(
    obj: Leaf, action: Action, iobj: Leaf | None, ctx: ExecutionToken | None
) -> tuple[ExecResult, ActionResult] | ActionResult:
    func: ActionActivateFunc = action.activate
    if ctx:
        # set context to action.activate call
        func = partial(func, ctx=ctx)

    if action.requires_object():
        return func(obj, iobj)

    return func(obj)


def _activate_action_multiple(
    obj: Leaf, action: Action, iobj: Leaf | None, ctx: ExecutionToken | None
) -> tuple[ExecResult, ActionResult] | ActionResult | None:
    objs = get_leaf_members(obj)

    if not hasattr(action, "activate_multiple"):
        iobjs = (None,) if iobj is None else get_leaf_members(iobj)
        return _activate_action_multiple_multiplied(objs, action, iobjs, ctx)

    func: ActionActivateMultipleFunc = action.activate_multiple
    if ctx:
        func = partial(func, ctx=ctx)

    if action.requires_object():
        iobjs = (None,) if iobj is None else get_leaf_members(iobj)
        return func(objs, iobjs)

    return func(objs)


def _activate_action_multiple_multiplied(
    objs: ty.Iterable[Leaf],
    action: Action,
    iobjs: ty.Iterable[Leaf | None],
    ctx: ExecutionToken | None,
) -> tuple[ExecResult, ActionResult] | ActionResult | None:
    """
    Multiple dispatch by "multiplied" invocation of the simple activation

    When action is delegated return (ExecResult, ActionResult), otherwise
    return ActionResult

    """
    rets = [
        _activate_action_single(leaf, action, item, ctx)
        for leaf in objs
        for item in iobjs
    ]

    actx = default_action_execution_context()
    return actx.combine_action_result_multiple(action, rets)


def parse_action_result(action: Action, ret: ActionResult) -> ExecResult:
    """Return result type for @action and return value @ret"""
    if ret is ActionResultRefresh:
        return ExecResult.REFRESH

    if not ret or (hasattr(ret, "is_valid") and not ret.is_valid()):
        return ExecResult.NONE

    # handle actions returning "new contexts"
    res = ExecResult.NONE
    if action.is_factory():
        res = ExecResult.SOURCE

    if action.has_result():
        res = ExecResult.OBJECT
    elif action.is_async():
        res = ExecResult.ASYNC

    return res


def _parse_late_action_result(action: Action, ret: ty.Any) -> int:
    # Late result is assumed to be a Leaf (Object) result
    # by default for backward compat.
    #
    # It is also allowed to be a Source

    if ret is ActionResultRefresh:
        return ExecResult.REFRESH

    if not ret or (hasattr(ret, "is_valid") and not ret.is_valid()):
        return ExecResult.NONE

    if isinstance(ret, Source):
        return ExecResult.SOURCE

    return ExecResult.OBJECT
