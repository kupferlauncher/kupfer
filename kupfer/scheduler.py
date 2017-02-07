
from gi.repository import GLib, GObject


from kupfer import pretty
from kupfer.weaklib import gobject_connect_weakly

_scheduler = None

def GetScheduler():
    """Get the shared instance"""
    global _scheduler
    if not _scheduler:
        _scheduler = Scheduler()
    return _scheduler

class Scheduler (GObject.GObject, pretty.OutputMixin):
    __gtype_name__ = "Scheduler"
    def __init__(self):
        super(Scheduler, self).__init__()
        self._finished = False

    def load(self):
        self.output_debug("Loading")
        self.emit("load")
        self.emit("loaded")
        self.output_debug("Loaded")

    def display(self):
        self.output_debug("Display")
        self.emit("display")
        GLib.idle_add(self._after_display)

    def _after_display(self):
        self.output_debug("After Display")
        self.emit("after-display")

    @property
    def finished(self):
        return self._finished

    def finish(self):
        self._finished = True
        self.emit("finish")
GObject.signal_new("load", Scheduler, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
GObject.signal_new("loaded", Scheduler, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
GObject.signal_new("display", Scheduler, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
GObject.signal_new("after-display", Scheduler, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())
GObject.signal_new("finish", Scheduler, GObject.SignalFlags.RUN_LAST,
        GObject.TYPE_BOOLEAN, ())

class Timer (object):
    def __init__(self, call_at_finish=False):
        self._current_timer = -1
        self._call_at_finish = call_at_finish
        self._current_callback = None
        gobject_connect_weakly(GetScheduler(), "finish", self._on_finish)

    def set(self, timeout_seconds, callback, *arguments):
        """Setup timer to call @timeout_seconds in the future.
        If the timer was previously set, it is postponed
        """
        self.invalidate()
        self._current_callback = lambda : callback(*arguments)
        self._current_timer = GLib.timeout_add_seconds(timeout_seconds,
                self._call)

    def set_ms(self, timeout_milliseconds, callback, *arguments):
        """Setup timer to call @timeout_milliseconds in the future.
        If the timer was previously set, it is postponed
        """
        self.invalidate()
        self._current_callback = lambda : callback(*arguments)
        self._current_timer = GLib.timeout_add(int(timeout_milliseconds),
                self._call)

    def set_idle(self, callback, *arguments):
        self.invalidate()
        self._current_callback = lambda : callback(*arguments)
        self._current_timer = GLib.idle_add(self._call)

    def _call(self, timer=None):
        self._current_timer = -1
        self._current_callback()
    
    def invalidate(self):
        if self._current_timer > 0:
            GLib.source_remove(self._current_timer)
        self._current_timer = -1

    def is_valid(self):
        """If Timer is currently set"""
        return (self._current_timer > 0)

    def _on_finish(self, scheduler):
        if self._call_at_finish and self.is_valid():
            self._call()
        else:
            self.invalidate()
