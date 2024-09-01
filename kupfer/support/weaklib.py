"""
This module is a part of the program Kupfer, see the main program file for
more information.
"""
from __future__ import annotations

import sys
import typing as ty
import weakref

if ty.TYPE_CHECKING:
    from gi.repository import GObject

__all__ = (
    "WeakCallback",
    "DbusWeakCallback",
    "GobjectWeakCallback",
    "gobject_connect_weakly",
)

MCallback = ty.Callable[..., None]


class WeakCallback:
    """A Weak Callback object that will keep a reference to
    the connecting object with weakref semantics.

    This allows object A to pass a callback method to object S,
    without object S keeping A alive.
    """

    def __init__(self, mcallback: MCallback) -> None:
        """Create a new Weak Callback calling the method @mcallback"""
        # pylint: disable=no-member
        obj = mcallback.__self__  # type: ignore
        # pylint: disable=no-member
        attr = mcallback.__func__.__name__  # type: ignore
        self.wref = weakref.ref(obj, self.object_deleted)
        self.callback_attr = attr
        self.token = None

    def __call__(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        if obj := self.wref():
            attr = getattr(obj, self.callback_attr)
            attr(*args, **kwargs)
        else:
            self.default_callback(*args, **kwargs)

    def default_callback(self, *args: ty.Any, **kwargs: ty.Any) -> None:
        """Called instead of callback when expired"""

    def object_deleted(self, wref: weakref.ReferenceType[ty.Any]) -> None:
        """Called when callback expires"""


class DbusWeakCallback(WeakCallback):
    """
    Will use @token if set as follows:
        token.remove()
    """

    def object_deleted(self, wref: weakref.ReferenceType[ty.Any]) -> None:
        # App is shutting down
        try:
            if sys.is_finalizing():
                return
        except AttributeError:
            if sys is None:
                return

        if self.token:
            self.token.remove()
            self.token = None


def dbus_signal_connect_weakly(
    bus: ty.Any, signal: str, mcallback: MCallback, **kwargs: ty.Any
) -> None:
    """
    Connect method @mcallback to dbus signal using a weak callback

    Connect to @signal on @bus, passing on all keyword arguments
    """
    weak_cb = DbusWeakCallback(mcallback)
    weak_cb.token = bus.add_signal_receiver(weak_cb, signal, **kwargs)


class GobjectWeakCallback(WeakCallback):
    """
    Will use @token if set as follows:
        sender.disconnect(token)
    """

    __senders: ty.ClassVar[dict[ty.Any, GObject]] = {}

    def object_deleted(self, wref: weakref.ReferenceType[GObject]) -> None:
        # App is shutting down
        try:
            if sys.is_finalizing():
                return
        except AttributeError:
            if sys is None:
                return

        sender = self.__senders.pop(self.token, None)
        if sender is not None:
            sender.disconnect(self.token)

    @classmethod
    def _connect(
        cls,
        sender: GObject,
        signal: str,
        mcallback: MCallback,
        *user_args: ty.Any,
    ) -> None:
        # We save references to the sender in a class variable,
        # this is the only way to have it accessible when obj expires.
        wcb = cls(mcallback)
        wcb.token = sender.connect(signal, wcb, *user_args)
        cls.__senders[wcb.token] = sender


def gobject_connect_weakly(
    sender: GObject, signal: str, mcallback: MCallback, *user_args: ty.Any
) -> None:
    """Connect weakly to GObject @sender's @signal,
    with a callback method @mcallback

    >>> import gi
    >>> gi.require_version("Gtk", "3.0")
    >>> from gi.repository import Gtk
    >>> btn = Gtk.Button.new()
    >>> class Handler (object):
    ...   def handle(self): pass
    ...   def __del__(self): print("deleted")
    ...
    >>> h = Handler()
    >>> gobject_connect_weakly(btn, "clicked", h.handle)
    >>> del h
    deleted
    >>>
    """
    # pylint: disable=protected-access
    GobjectWeakCallback._connect(  # noqa: SLF001
        sender, signal, mcallback, *user_args
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
