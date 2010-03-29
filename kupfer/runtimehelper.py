import gio

from kupfer.objects import FileLeaf
from kupfer import commandexec

def register_async_file_result(filepath):
	"This function may only be called inside command execution"
	ctx = commandexec.DefaultActionExecutionContext()
	return AsyncFileResult(ctx.get_async_token(), filepath)

class AsyncFileResult (object):
	"""Expect a given file path to be created, and when (probably) done,
	post the file as a late result.
	"""
	def __init__(self, async_token, filepath):
		self.async_token = async_token
		gfile = gio.File(filepath)
		self.monitor = gfile.monitor_file(gio.FILE_MONITOR_NONE)
		self.callback_id = self.monitor.connect("changed", self.changed)

	def changed(self, monitor, gfile1, gfile2, event):
		if event == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
			ctx = commandexec.DefaultActionExecutionContext()
			ctx.register_late_result(self.async_token,
					FileLeaf(gfile1.get_path()))
			self.monitor.disconnect(self.callback_id)
			self.monitor = None


