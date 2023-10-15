"""
Application - related objects (leaves, sources)

This file is a part of the program kupfer, which is
released under GNU General Public License v3 (or any later version),
see the main program file, and COPYING for details.
"""
from __future__ import annotations

import os
import typing as ty
from contextlib import suppress

from gi.repository import Gio, GLib

from kupfer import launch, icons
from kupfer.support import pretty
from kupfer.version import DESKTOP_ID

from kupfer.obj.base import Action, Leaf, Source
from kupfer.obj.exceptions import InvalidDataError, OperationError
from kupfer.obj.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer.core import commandexec

if ty.TYPE_CHECKING:
    from gettext import gettext as _

__all__ = (
    "AppLeafContentMixin",
    "ApplicationSource",
    "AppLeaf",
    "Launch",
    "LaunchAgain",
    "CloseAll",
)


class AppLeafContentMixin:
    """Mixin for Source that correspond one-to-one with a AppLeaf.

    This Mixin sees to that the Source is set as content for the application
    with id 'cls.appleaf_content_id', which may also be a sequence of ids.

    Source has to define the attribute appleaf_content_id and must
    inherit this mixin BEFORE the Source

    This Mixin defines:
    get_leaf_repr
    decorates_type,
    decorates_item
    """

    _cached_leaf_repr: AppLeaf | None

    @classmethod
    def get_leaf_repr(cls) -> AppLeaf | None:
        if not hasattr(cls, "_cached_leaf_repr"):
            cls._cached_leaf_repr = cls.__get_leaf_repr()

        return cls._cached_leaf_repr

    @classmethod
    def __get_appleaf_id_iter(cls) -> ty.Iterator[str]:
        assert hasattr(cls, "appleaf_content_id")
        if isinstance(cls.appleaf_content_id, str):
            yield cls.appleaf_content_id
        else:
            yield from cls.appleaf_content_id

    @classmethod
    def __get_leaf_repr(cls) -> AppLeaf | None:
        for appleaf_id in cls.__get_appleaf_id_iter():
            with suppress(InvalidDataError):
                return AppLeaf(app_id=appleaf_id)

        return None

    @classmethod
    def decorates_type(cls) -> ty.Type[Leaf]:
        return AppLeaf

    @classmethod
    def decorate_item(cls, leaf: Leaf) -> AppLeafContentMixin | None:
        if leaf == cls.get_leaf_repr():
            return cls()

        return None


class ApplicationSource(
    AppLeafContentMixin, Source, PicklingHelperMixin, FilesystemWatchMixin
):
    """Abstract, helper class that include parent object to create source that
    is bound to application leaf with file/folders monitoring."""


class AppLeaf(Leaf):
    LOAD_EXTRA_ALIASES: bool = False

    def __init__(
        self,
        item: ty.Any = None,
        init_path: str | None = None,
        app_id: str | None = None,
        require_x: bool = True,
    ) -> None:
        """Try constructing an Application for GAppInfo @item,
        for file @path or for package name @app_id.

        @require_x: require executable file

        Represented object is Gio.DesktopAppInfo.
        """
        self._init_path = init_path
        self._init_item_id = app_id and app_id + ".desktop"
        # finish will raise InvalidDataError on invalid item
        self._finish(require_x, item)
        super().__init__(self.object, self.object.get_name())
        self._add_aliases()

    def _add_aliases(self) -> None:
        # find suitable alias
        # use package name: non-extension part of ID
        package_name = GLib.filename_display_basename(self.get_id())
        if package_name and package_name not in str(self).lower():
            self.kupfer_add_alias(package_name)

        # add executable as alias
        if cmdl := self.object.get_executable():
            self.kupfer_add_alias(cmdl)

        # do not continue when application setting "load extra aliases" if off
        if not AppLeaf.LOAD_EXTRA_ALIASES:
            return

        # add non-localized name
        if (en_name := self.object.get_string("Name")) != self.name:
            self.kupfer_add_alias(en_name)

        # add generic name
        if (
            name := (
                self.object.get_string("GenericName")
                or self.object.get_string("GenericName")
            )
        ) and name != self.name:
            self.kupfer_add_alias(name)

        # add keywords
        if keywords := self.object.get_string_list("Keywords"):
            for keyword in keywords:
                self.kupfer_add_alias(keyword)

        # add Comment
        if comment := (
            self.object.get_locale_string("Comment")
            or self.object.get_string("Comment")
        ):
            self.kupfer_add_alias(comment)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: ty.Any) -> bool:
        return isinstance(other, type(self)) and self.get_id() == other.get_id()

    def __getstate__(self) -> dict[str, ty.Any]:
        self._init_item_id = self.object and self.object.get_id()
        state = dict(vars(self))
        state["object"] = None
        return state

    def __setstate__(self, state: dict[str, ty.Any]) -> None:
        vars(self).update(state)
        self._finish()

    def _finish(
        self,
        require_x: bool = False,
        item: Gio.DesktopAppInfo | None = None,
    ) -> None:
        """Try to set self.object from init's parameters"""
        if not item:
            # Construct an AppInfo item from either path or item_id
            try:
                if self._init_path and (
                    not require_x or os.access(self._init_path, os.X_OK)
                ):
                    # serilizable if created from a "loose file"
                    self.serializable = 1
                    item = Gio.DesktopAppInfo.new_from_filename(self._init_path)
                elif self._init_item_id:
                    item = Gio.DesktopAppInfo.new(self._init_item_id)

            except TypeError as exc:
                pretty.print_debug(
                    __name__,
                    "Application not found:",
                    self._init_item_id,
                    self._init_path,
                )
                raise InvalidDataError from exc

        self.object = item
        if not self.object:
            raise InvalidDataError

    def repr_key(self) -> ty.Any:
        return self.get_id()

    def launch(
        self,
        files: ty.Iterable[Gio.File] = (),
        paths: ty.Iterable[str] = (),
        activate: bool = False,
        ctx: commandexec.ExecutionToken | None = None,
        work_dir: str | None = None,
        uris: ty.Iterable[str] = (),
    ) -> bool:
        """Launch the represented applications.

        `files` is a sequence of GFiles (Gio.File), `paths` is a sequence of
        paths (str), `uris` is list of uri. All three lists are combined
        together. In most cases only one list should be passed to this method.

        When `activate` is True - activate running instance instead of start
        new.

        `work_dir` can overwrite work directory of application.
        """
        try:
            return launch.launch_application(
                self.object,
                files=files,
                paths=paths,
                uris=uris,
                activate=activate,
                desktop_file=self._init_path,
                screen=ctx and ctx.environment.get_screen(),
                work_dir=work_dir,
            )
        except launch.SpawnError as exc:
            raise OperationError(exc) from exc

    def get_id(self) -> str:
        """Return the unique ID for this app.

        This is the GIO id "gedit.desktop" minus the .desktop part for
        system-installed applications.
        """
        return launch.application_id(self.object, self._init_path)

    def get_actions(self) -> ty.Iterable[Action]:
        id_ = self.get_id()
        if id_ == DESKTOP_ID:
            return

        if launch.application_is_running(id_):
            yield Launch(_("Go To"), is_running=True)
            yield CloseAll()
        else:
            yield Launch()

        yield LaunchAgain()

    def get_description(self) -> str | None:
        # Use Application's description, else use executable
        # for "file-based" applications we show the path
        app_desc = self.object.get_description()
        ret: str = app_desc or self.object.get_executable()
        if self._init_path:
            app_path = launch.get_display_path_for_bytestring(self._init_path)
            return f"({app_path}) {ret}"

        return ret

    def get_gicon(self) -> icons.GIcon | None:
        return self.object.get_icon()

    def get_icon_name(self) -> str:
        return "exec"


class Launch(Action):
    """Launches an application (AppLeaf)"""

    action_accelerator: str | None = "o"
    rank_adjust = 5

    def __init__(
        self,
        name: str | None = _("Launch"),
        is_running: bool = False,
        open_new: bool = False,
    ) -> None:
        """
        If @is_running, style as if the app is running (Show application)
        If @open_new, always start a new instance.
        """
        Action.__init__(self, name)
        self.is_running = is_running
        self.open_new = open_new

    def wants_context(self) -> bool:
        return True

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert isinstance(leaf, AppLeaf)
        leaf.launch(activate=not self.open_new, ctx=ctx)
        return None

    def get_description(self) -> str:
        if self.is_running:
            return _("Show application window")

        return _("Launch application")

    def get_icon_name(self) -> str:
        if self.is_running:
            return "go-jump"

        return "kupfer-launch"


class LaunchAgain(Launch):
    action_accelerator: str | None = None
    rank_adjust = 0

    def __init__(self, name: str | None = _("Launch Again")):
        Launch.__init__(self, name, open_new=True)

    def item_types(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield AppLeaf

    def valid_for_item(self, leaf: Leaf) -> bool:
        assert isinstance(leaf, AppLeaf)
        return launch.application_is_running(leaf.get_id())

    def get_description(self) -> str:
        return _("Launch another instance of this application")


class CloseAll(Action):
    """Attempt to close all application windows"""

    rank_adjust = -10

    def __init__(self, name: str | None = _("Close")) -> None:
        Action.__init__(self, name)

    def activate(
        self,
        leaf: Leaf,
        iobj: Leaf | None = None,
        ctx: commandexec.ExecutionToken | None = None,
    ) -> Leaf | None:
        assert isinstance(leaf, AppLeaf)
        launch.application_close_all(leaf.get_id())
        return None

    def item_types(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield AppLeaf

    def valid_for_item(self, leaf: Leaf) -> bool:
        assert isinstance(leaf, AppLeaf)
        return launch.application_is_running(leaf.get_id())

    def get_description(self) -> str:
        return _("Attempt to close all application windows")

    def get_icon_name(self) -> str:
        return "window-close"
