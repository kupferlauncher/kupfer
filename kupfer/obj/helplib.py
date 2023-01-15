"""
This module contains Helper constructs

This module is a part of the program Kupfer, see the main program file for
more information.
"""

import typing as ty

from gi.repository import Gio, GLib

from kupfer.support import pretty

from .base import Action, Leaf, Source


class PicklingHelperMixin:
    """This pickling helper will define __getstate__/__setstate__
    acting simply on the class dictionary; it is up to the inheriting
    class to set up:
    pickle_prepare:
        Modify the instance dict to remove any unpickleable attributes,
        the resulting dict will be pickled
    unpickle_finish:
        Finish unpickling by restoring nonpickled attributes from the
        saved class dict, or setting up change callbacks or similar
    """

    def pickle_prepare(self) -> None:
        pass

    def unpickle_finish(self) -> None:
        pass

    def __getstate__(self) -> ty.Dict[str, ty.Any]:
        """On pickle, getstate will call self.pickle_prepare(),
        then it will return the class' current __dict__
        """
        self.pickle_prepare()
        return self.__dict__

    def __setstate__(self, state: ty.Dict[str, ty.Any]) -> None:
        """On unpickle, setstate will restore the class' __dict__,
        then call self.unpickle_finish()
        """
        self.__dict__.update(state)
        self.unpickle_finish()


class NonpersistentToken(PicklingHelperMixin):
    """A token will keep a reference until pickling, when it is deleted"""

    def __init__(self, data: ty.Any):
        self.data = data

    def __bool__(self) -> bool:
        return bool(self.data)

    def pickle_prepare(self) -> None:
        self.data = None


class FilesystemWatchMixin:
    """A mixin for Sources watching directories"""

    def monitor_directories(
        self, *directories: str, **kwargs: ty.Any
    ) -> NonpersistentToken:
        """Register @directories for monitoring;

        On changes, the Source will be marked for update.
        This method returns a monitor token that has to be
        stored for the monitor to be active.

        The token will be a false value if nothing could be monitored.

        Nonexisting directories are skipped, if not passing
        the kwarg @force
        """
        tokens = []
        force = kwargs.get("force", False)
        for directory in directories:
            gfile = Gio.File.new_for_path(directory)
            if not force and not gfile.query_exists():
                continue

            try:
                monitor = gfile.monitor_directory(
                    Gio.FileMonitorFlags.NONE, None
                )
            except GLib.GError as exc:
                pretty.print_debug(__name__, "FilesystemWatchMixin", exc)
                continue

            if monitor:
                monitor.connect("changed", self.__directory_changed)
                tokens.append(monitor)

        return NonpersistentToken(tokens)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        """Return whether @gfile should trigger an update event
        by default, files beginning with "." are ignored
        """
        return not (gfile and gfile.get_basename().startswith("."))

    def __directory_changed(
        self,
        _monitor: ty.Any,
        file1: Gio.File,
        _file2: ty.Any,
        evt_type: Gio.FileMonitorEvent,
    ) -> None:
        if evt_type in (
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.DELETED,
        ) and self.monitor_include_file(file1):
            self.mark_for_update()  # type: ignore


def reverse_action(action: ty.Type[Action], rank: int = 0) -> ty.Type[Action]:
    """Return a reversed version a three-part action

    @action: the action class
    @rank: the rank_adjust to give the reversed action

    A three-part action requires a direct object (item) and an indirect
    object (iobj).

    In general, the item must be from the Catalog, while the iobj can be
    from one, specified special Source. If this is used, and the action
    will be reversed, the base action must be the one specifying a
    source for the iobj. The reversed action will always take both item
    and iobj from the Catalog, filtered by type.

    If valid_object(iobj, for_leaf=None) is used, it will always be
    called with only the new item as the first parameter when reversed.
    """

    class ReverseAction(action):
        rank_adjust = rank

        def activate(
            self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
        ) -> ty.Any:
            return action.activate(self, iobj, leaf, ctx)

        def item_types(self) -> ty.Iterable[ty.Type[Leaf]]:
            return action.object_types(self)

        def valid_for_item(self, leaf: Leaf) -> bool:
            try:
                return action.valid_object(self, leaf)  # type: ignore
            except AttributeError:
                return True

        def object_types(self) -> ty.Iterable[ty.Type[Leaf]]:
            return action.item_types(self)

        def valid_object(
            self, obj: Leaf, for_item: ty.Optional[Leaf] = None
        ) -> bool:
            return action.valid_for_item(self, obj)

        def object_source(
            self, for_item: ty.Optional[Leaf] = None
        ) -> ty.Optional[Source]:
            return None

    ReverseAction.__name__ = "Reverse" + action.__name__
    return ReverseAction
