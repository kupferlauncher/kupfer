from __future__ import annotations

import typing as ty

from gi.repository import GLib, GObject

from kupfer.support import pretty, weaklib


def get_scheduler() -> Scheduler:
    """Get the shared instance"""
    return Scheduler.instance()


class Scheduler(GObject.GObject, pretty.OutputMixin):  # type:ignore
    __gtype_name__ = "Scheduler"

    _instance: Scheduler | None = None

    @classmethod
    def instance(cls) -> Scheduler:
        if cls._instance is None:
            cls._instance = Scheduler()

        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self._finished = False

    def load(self) -> None:
        self.output_debug("Loading")
        self.emit("load")
        self.emit("loaded")
        self.output_debug("Loaded")

    def display(self) -> None:
        self.output_debug("Display")
        self.emit("display")
        GLib.idle_add(self._after_display)

    def _after_display(self) -> None:
        self.output_debug("After Display")
        self.emit("after-display")

    @property
    def finished(self) -> bool:
        return self._finished

    def finish(self) -> None:
        self._finished = True
        self.emit("finish")


GObject.signal_new(
    "load", Scheduler, GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ()
)
GObject.signal_new(
    "loaded", Scheduler, GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ()
)
GObject.signal_new(
    "display",
    Scheduler,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
GObject.signal_new(
    "after-display",
    Scheduler,
    GObject.SignalFlags.RUN_LAST,
    GObject.TYPE_BOOLEAN,
    (),
)
GObject.signal_new(
    "finish", Scheduler, GObject.SignalFlags.RUN_LAST, GObject.TYPE_BOOLEAN, ()
)


TimerCallback = ty.Callable[..., None]


class Timer:
    def __init__(self, call_at_finish: bool = False) -> None:
        self._current_timer = -1
        self._call_at_finish = call_at_finish
        self._current_callback: ty.Callable[[], None] | None = None
        weaklib.gobject_connect_weakly(
            get_scheduler(), "finish", self._on_finish
        )

    def set(
        self,
        timeout_seconds: float,
        callback: TimerCallback,
        *arguments: ty.Any,
    ) -> None:
        """Setup timer to call @timeout_seconds in the future.
        If the timer was previously set, it is postponed
        """
        self.invalidate()
        self._current_callback = lambda: callback(*arguments)
        self._current_timer = GLib.timeout_add_seconds(
            timeout_seconds, self._call
        )

    def set_ms(
        self,
        timeout_milliseconds: int,
        callback: TimerCallback,
        *arguments: ty.Any,
    ) -> None:
        """Setup timer to call @timeout_milliseconds in the future.
        If the timer was previously set, it is postponed
        """
        self.invalidate()
        self._current_callback = lambda: callback(*arguments)
        self._current_timer = GLib.timeout_add(
            int(timeout_milliseconds), self._call
        )

    def set_idle(self, callback: TimerCallback, *arguments: ty.Any) -> None:
        self.invalidate()
        self._current_callback = lambda: callback(*arguments)
        self._current_timer = GLib.idle_add(self._call)

    def _call(self, timer: ty.Any = None) -> None:
        assert self._current_callback

        self._current_timer = -1
        self._current_callback()

    def invalidate(self) -> None:
        if self._current_timer > 0:
            GLib.source_remove(self._current_timer)

        self._current_timer = -1

    def is_valid(self) -> bool:
        """If Timer is currently set"""
        return self._current_timer > 0

    def _on_finish(self, _scheduler: ty.Any) -> None:
        if self._call_at_finish and self.is_valid():
            self._call()
        else:
            self.invalidate()
