from __future__ import annotations

from gi.repository import Gio

from kupfer.core.commandexec import ExecutionToken
from kupfer.obj import FileLeaf


# pylint: disable=too-few-public-methods
class AsyncFileResult:
    """Expect a given file path to be created, and when (probably) done,
    post the file as a late result.

    FIXME: add some timeout and not wait forever
    """

    def __init__(self, ctx: ExecutionToken, filepath: str) -> None:
        self.ctx = ctx
        gfile = Gio.File.new_for_path(filepath)
        self.monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE)
        self.callback_id = self.monitor.connect("changed", self._on_changed)

    def _on_changed(
        self,
        monitor: Gio.FileMonitor,
        gfile1: Gio.File,
        gfile2: Gio.File | None,
        event: Gio.FileMonitorEvent,
    ) -> None:
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.ctx.register_late_result(FileLeaf(gfile1.get_path()))
            self.monitor.disconnect(self.callback_id)
            self.monitor = None


def register_async_file_result(
    ctx: ExecutionToken, filepath: str
) -> AsyncFileResult:
    """Register that @filepath may appear soon.
    @ctx: The action's execution context token
    """
    return AsyncFileResult(ctx, filepath)
