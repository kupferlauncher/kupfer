"""
This module contains Helper constructs

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import typing as ty
from pathlib import Path

from gi.repository import Gio, GLib

from kupfer.support import pretty
from kupfer.obj import base
from kupfer.core import commandexec

__all__ = (
    "PicklingHelperMixin",
    "NonpersistentToken",
    "reverse_action",
)


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

    def __getstate__(self) -> dict[str, ty.Any]:
        """On pickle, getstate will call self.pickle_prepare(),
        then it will return the class' current __dict__."""
        self.pickle_prepare()
        return self.__dict__

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        """On unpickle, setstate will restore the class' __dict__,
        then call self.unpickle_finish()."""
        self.__dict__.update(state)
        self.unpickle_finish()


TokenDataT = ty.TypeVar("TokenDataT")


class NonpersistentToken(PicklingHelperMixin, ty.Generic[TokenDataT]):
    """A token will keep a reference until pickling, when it is deleted"""

    data: TokenDataT | None

    def __init__(self, data: TokenDataT):
        self.data = data

    def __bool__(self) -> bool:
        return bool(self.data)

    def pickle_prepare(self) -> None:
        self.data = None


FileMonitorToken = NonpersistentToken[list[Gio.FileMonitor]]


class FilesystemWatchMixin:
    """A mixin for Sources watching directories"""

    def monitor_files(self, *files: str | Path) -> FileMonitorToken:
        """Start monitoring `files` for changes.
        Similar `monitor_directories`, but monitor also not existing files."""
        tokens = []
        for file in files:
            if isinstance(file, Path):
                file = str(file)

            gfile = Gio.File.new_for_path(file)
            try:
                monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            except GLib.GError as exc:
                pretty.print_debug(__name__, "FilesystemWatchMixin", exc)
                continue

            if monitor:
                monitor.connect("changed", self._on_file_changed)
                tokens.append(monitor)

        return NonpersistentToken(tokens)

    def monitor_directories(
        self, *directories: str | Path, force: bool = False
    ) -> FileMonitorToken:
        """Register @directories for monitoring;

        On changes, the Source will be marked for update.
        This method returns a monitor token that has to be
        stored for the monitor to be active.

        The token will be a false value if nothing could be monitored.

        Nonexisting directories are skipped, if not passing `force` True.
        """
        tokens = []
        for directory in directories:
            if isinstance(directory, Path):
                directory = str(directory)

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
                monitor.connect("changed", self._on_directory_changed)
                tokens.append(monitor)

        return NonpersistentToken(tokens)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        """Return whether @gfile should trigger an update event
        by default, files beginning with "." are ignored.

        This method is used for monitoring both files and directories.
        """
        return not (gfile and gfile.get_basename().startswith("."))

    def stop_monitor_fs_changes(self, nptoken: FileMonitorToken | None) -> None:
        """Stop monitoring for files or directories changes"""
        if nptoken and nptoken.data:
            for token in nptoken.data:
                assert isinstance(token, Gio.FileMonitor)
                token.cancel()

    def _on_directory_changed(
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
            assert hasattr(self, "mark_for_update")
            self.mark_for_update()

    def _on_file_changed(
        self,
        _monitor: ty.Any,
        file1: Gio.File,
        _file2: ty.Any,
        evt_type: Gio.FileMonitorEvent,
    ) -> None:
        if evt_type in (
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.DELETED,
            Gio.FileMonitorEvent.CHANGED,
        ) and self.monitor_include_file(file1):
            assert hasattr(self, "mark_for_update")
            self.mark_for_update()


def reverse_action(
    action: ty.Type[base.Action], rank: int = 0
) -> ty.Type[base.Action]:
    """Return a reversed version a three-part action.

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

    class ReverseAction(action):  # type: ignore
        rank_adjust = rank

        def activate(
            self,
            leaf: base.Leaf,
            iobj: base.Leaf | None = None,
            ctx: commandexec.ExecutionToken | None = None,
        ) -> ty.Any:
            assert iobj
            return action.activate(self, iobj, leaf, ctx)

        def item_types(self) -> ty.Iterable[ty.Type[base.Leaf]]:
            return action.object_types(self)

        def valid_for_item(self, leaf: base.Leaf) -> bool:
            try:
                return action.valid_object(self, leaf)  # type: ignore
            except AttributeError:
                return True

        def object_types(self) -> ty.Iterable[ty.Type[base.Leaf]]:
            return action.item_types(self)

        def valid_object(
            self, obj: base.Leaf, for_item: base.Leaf | None = None
        ) -> bool:
            return action.valid_for_item(self, obj)

        def object_source(
            self, for_item: base.Leaf | None = None
        ) -> base.Source | None:
            return None

    ReverseAction.__name__ = "Reverse" + action.__name__
    return ReverseAction
