
import gobject

from kupfer import pretty

_scheduler = None

def GetScheduler():
	"""Get the shared instance"""
	global _scheduler
	if not _scheduler:
		_scheduler = Scheduler()
	return _scheduler

class Scheduler (gobject.GObject, pretty.OutputMixin):
	__gtype_name__ = "Scheduler"
	def __init__(self):
		super(Scheduler, self).__init__()
	def load(self):
		self.output_debug("Loading")
		self.emit("load")
		self.emit("loaded")
		self.output_debug("Loaded")
	def finish(self):
		self.emit("finish")
gobject.signal_new("load", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("loaded", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("finish", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())

class Timer (gobject.GObject):
	def __init__(self, call_at_finish=False):
		self._current_timer = -1
		self._call_at_finish = call_at_finish
		self._current_callback = None
		GetScheduler().connect("finish", self._on_finish)

	def set(self, timeout_seconds, callback, *arguments):
		"""Setup timer to call @timeout_seconds in the future.
		If the timer was previously set, it is postponed
		"""
		self.invalidate()
		self._current_callback = lambda : callback(*arguments)
		self._current_timer = gobject.timeout_add_seconds(timeout_seconds,
				self._call)

	def _call(self, timer=None):
		self._current_timer = -1
		self._current_callback()
	
	def invalidate(self):
		if self._current_timer > 0:
			gobject.source_remove(self._current_timer)
		self._current_timer = -1

	def is_valid(self):
		"""If Timer is currently set"""
		return (self._current_timer > 0)

	def _on_finish(self, scheduler):
		if self._call_at_finish and self.is_valid():
			self._call()
		else:
			self.invalidate()
