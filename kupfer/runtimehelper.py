from gi.repository import Gio

from kupfer.objects import FileLeaf

def register_async_file_result(ctx, filepath):
    """
    Register that @filepath may appear soon
    @ctx: The action's execution context token
    """
    return AsyncFileResult(ctx, filepath)

class AsyncFileResult (object):
    """Expect a given file path to be created, and when (probably) done,
    post the file as a late result.
    """
    def __init__(self, ctx, filepath):
        self.ctx = ctx
        gfile = Gio.File.new_for_path(filepath)
        self.monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE)
        self.callback_id = self.monitor.connect("changed", self.changed)

    def changed(self, monitor, gfile1, gfile2, event):
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.ctx.register_late_result(FileLeaf(gfile1.get_path()))
            self.monitor.disconnect(self.callback_id)
            self.monitor = None


