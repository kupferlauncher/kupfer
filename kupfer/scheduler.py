
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
		self.emit("load")
		self.emit("loaded")
	def finish(self):
		self.emit("finish")
gobject.signal_new("load", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("loaded", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
gobject.signal_new("finish", Scheduler, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())
