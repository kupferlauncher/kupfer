from __future__ import annotations

import typing as ty

from gi.repository import Gio

from kupfer.core.commandexec import ExecutionToken
from kupfer.obj import FileLeaf
from kupfer.support import scheduler

__all__ = ("AsyncFileResult", "register_async_file_result")


# pylint: disable=too-few-public-methods
class AsyncFileResult:
    """Expect a given file path to be created, and when (probably) done,
    post the file as a late result."""

    def __init__(
        self, ctx: ExecutionToken, filepath: str, timeout: int = 0
    ) -> None:
        self.ctx = ctx
        gfile = Gio.File.new_for_path(filepath)
        self.monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE)
        self.callback_id = self.monitor.connect("changed", self._on_changed)
        self._cancel_timer = None
        if timeout:
            self._cancel_timer = scheduler.Timer(True)
            self._cancel_timer.set(timeout, self._cancel)

    def _cancel(self, *_args: ty.Any) -> None:
        """Stop waiting for file."""
        self.monitor.disconnect(self.callback_id)
        self.monitor.cancel()
        self.monitor = None
        if self._cancel_timer:
            self._cancel_timer.invalidate()

    def _on_changed(
        self,
        monitor: Gio.FileMonitor,
        gfile1: Gio.File,
        gfile2: Gio.File | None,
        event: Gio.FileMonitorEvent,
    ) -> None:
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.ctx.register_late_result(FileLeaf(gfile1.get_path()))
            self._cancel()


def register_async_file_result(
    ctx: ExecutionToken, filepath: str, timeout: int = 600
) -> AsyncFileResult:
    """Register that `filepath` may appear soon.
    `ctx` is the action's execution context token.
    `timeout` is maximum time to wait for file.
    """
    return AsyncFileResult(ctx, filepath, timeout)
