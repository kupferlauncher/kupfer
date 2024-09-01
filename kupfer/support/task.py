from __future__ import annotations

import sys
import threading
import time
import typing as ty

from gi.repository import GLib

from kupfer.support import pretty, scheduler

if ty.TYPE_CHECKING:
    from kupfer.support.types import ExecInfo

__all__ = ("Task", "ThreadTask", "TaskRunner")

TaskCallback = ty.Callable[[ty.Any], None]


class Task:
    """Represent a task that can be done in the background

    The finish_callback received in Task.start(..) must be stored,
    and regardless if the task exits with an error, or completes
    successfully, the callback *must* be called.

    The finish callback must pass the Task instance itself as
    the only and first argument:

        finish_callback(self)
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = name

    def __repr__(self) -> str:
        name = repr(getattr(self, "name", None))
        return f"<{type(self).__module__}.{type(self).__name__} name={name}>"

    def start(self, finish_callback: TaskCallback) -> None:
        raise NotImplementedError


class ThreadTask(Task):
    """Run in a thread.

    `wait_sec` (when >0) specify time when we wait for result. After this
    time `thread_finish`, `finish_callback` and `thread_finally` are not called.
    We can't simply kill background thread but we can ignore its result and
    log errors (if any).
    """

    def __init__(self, name: str | None = None, wait_sec: int = 0):
        Task.__init__(self, name)
        self._finish_callback: TaskCallback | None = None
        # what long we wait for result; after this time _finish_callback is not
        # called
        self.wait_sec = wait_sec
        self.thread_started_ts: float = 0

    def thread_do(self) -> None:
        """Override this to run what should be done in the thread"""
        raise NotImplementedError

    def thread_finish(self) -> None:
        """This finish function runs in the main thread after thread
        completion, and can be used to communicate with the GUI.
        """

    def thread_finally(self, exc_info: ExecInfo | None) -> None:
        """Always run at thread finish"""
        if exc_info is not None:
            _etype, value, tback = exc_info
            if value:
                raise value.with_traceback(tback)

    def _thread_finally(self, exc_info: ExecInfo | None) -> None:
        try:
            self.thread_finally(exc_info)
        finally:
            if self._finish_callback:
                self._finish_callback(self)

    def _log_error(self, exc_info: ExecInfo | None) -> None:
        if exc_info:
            pretty.print_exc(__name__, exc_info)

    def _run_thread(self) -> None:
        exc_info = None
        overdue = False
        try:
            self.thread_do()
            overdue = self.wait_sec > 0 and (
                time.monotonic() - self.thread_started_ts > self.wait_sec
            )
            if not overdue:
                GLib.idle_add(self.thread_finish)

        except Exception:
            exc_info = sys.exc_info()
        finally:
            if overdue:
                GLib.idle_add(self._log_error, exc_info)
            else:
                GLib.idle_add(self._thread_finally, exc_info)

    def start(self, finish_callback: TaskCallback) -> None:
        self._finish_callback = finish_callback
        self.thread_started_ts = time.monotonic()
        thread = threading.Thread(target=self._run_thread)
        thread.start()


class TaskRunner(pretty.OutputMixin):
    """Run Tasks in the idle Loop"""

    def __init__(self, end_on_finish: bool) -> None:
        self.tasks: set[Task] = set()
        self.end_on_finish = end_on_finish
        scheduler.get_scheduler().connect("finish", self._on_finish)

    def _task_finished(self, task):
        self.output_debug("Task finished", task)
        self.tasks.remove(task)

    def add_task(self, task: Task) -> None:
        """Register @task to be run"""
        self.tasks.add(task)
        task.start(self._task_finished)

    def _on_finish(self, _sched: ty.Any) -> None:
        if self.end_on_finish:
            self.tasks.clear()
            return

        if self.tasks:
            self.output_info("Uncompleted tasks:")
            for task in self.tasks:
                self.output_info(task)
