#! /usr/bin/env python3

"""
File-related objects
"""
from __future__ import annotations

import os
import typing as ty
from contextlib import suppress
from os import path

from gi.repository import GdkPixbuf, Gio, GLib

from kupfer import icons, launch, utils
from kupfer.desktop_launch import SpawnError
from kupfer.support import kupferstring, pretty
from kupfer.version import DESKTOP_ID

from .base import Action, Leaf, Source
from .exceptions import (
    InvalidDataError,
    NoDefaultApplicationError,
    OperationError,
)
from .helplib import FilesystemWatchMixin, PicklingHelperMixin
from .representation import TextRepresentation

if ty.TYPE_CHECKING:
    _ = str


# FIXME: rename
def ConstructFileLeaf(obj: str) -> Leaf:
    """
    If the path in @obj points to a Desktop Item file,
    return an AppLeaf, otherwise return a FileLeaf
    """
    _root, ext = path.splitext(obj)
    if ext == ".desktop":
        with suppress(InvalidDataError):
            return AppLeaf(init_path=obj)

    return FileLeaf(obj)


class FileLeaf(Leaf, TextRepresentation):
    """
    Represents one file: the represented object is a bytestring (important!)
    """

    serializable: int | None = 1

    def __init__(
        self,
        obj: str,
        name: ty.Optional[str] = None,
        alias: ty.Optional[str] = None,
    ) -> None:
        """Construct a FileLeaf

        The display name of the file is normally derived from the full path,
        and @name should normally be left unspecified.

        @obj: byte string (file system encoding)
        @name: unicode name or None for using basename
        """
        if obj is None:
            raise InvalidDataError(f"File path for {name} may not be None")
        # Use glib filename reading to make display name out of filenames
        # this function returns a `unicode` object
        if not name:
            unicode_path = kupferstring.tounicode(obj)
            name = GLib.filename_display_basename(unicode_path)

        assert name
        super().__init__(obj, name)
        if alias:
            self.kupfer_add_alias(alias)

    @classmethod
    def from_uri(cls, uri: str) -> ty.Optional[FileLeaf]:
        """
        Construct a FileLeaf

        uri: A local uri

        Return FileLeaf if it is supported, else None
        """
        gfile = Gio.File.new_for_uri(uri)
        fpath = gfile.get_path()
        if fpath:
            return cls(fpath)

        return None

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: ty.Any) -> bool:
        try:
            return (
                type(self) is type(other)
                and str(self) == str(other)
                and path.samefile(self.object, other.object)
            )
        except OSError as exc:
            pretty.print_debug(__name__, exc)
            return False

    def repr_key(self) -> ty.Any:
        return self.object

    def canonical_path(self) -> str:
        """Return the true path of the File (without symlinks)"""
        return path.realpath(self.object)  # type: ignore

    def is_valid(self) -> bool:
        return os.access(self.object, os.R_OK)

    def is_writable(self) -> bool:
        return os.access(self.object, os.W_OK)

    def _is_executable(self) -> bool:
        return os.access(self.object, os.R_OK | os.X_OK)

    def is_dir(self) -> bool:
        return path.isdir(self.object)

    def get_text_representation(self) -> str:
        return GLib.filename_display_name(self.object)  # type: ignore

    def get_urilist_representation(self) -> ty.List[str]:
        return [self.get_gfile().get_uri()]

    def get_gfile(self) -> Gio.File:
        """
        Return a Gio.File of self
        """
        return Gio.File.new_for_path(self.object)

    def get_description(self) -> ty.Optional[str]:
        return utils.get_display_path_for_bytestring(self.canonical_path())

    def get_actions(self) -> ty.Iterable[Action]:
        yield Open()
        yield GetParent()

        if self.is_dir():
            yield OpenTerminal()

        elif self.is_valid():
            if self._is_good_executable():
                yield Execute()
                yield Execute(in_terminal=True)

    def has_content(self) -> bool:
        return self.is_dir() or Leaf.has_content(self)

    def content_source(self, alternate: bool = False) -> Source | None:
        if self.is_dir():
            return DirectorySource(self.object, show_hidden=alternate)

        return Leaf.content_source(self)

    def get_thumbnail(self, width: int, height: int) -> GdkPixbuf.Pixbuf | None:
        if self.is_dir():
            return None

        return icons.get_thumbnail_for_gfile(self.get_gfile(), width, height)

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        return icons.get_gicon_for_file(self.object)

    def get_icon_name(self) -> str:
        if self.is_dir():
            return "folder"

        return "text-x-generic"

    def get_content_type(self) -> ty.Optional[str]:
        ret, uncertain = Gio.content_type_guess(self.object, None)
        if not uncertain:
            return ret  # type: ignore

        content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
        gfile = self.get_gfile()
        if not gfile.query_exists(None):
            return None

        info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
        content_type = info.get_attribute_string(content_attr)
        return content_type  # type: ignore

    def is_content_type(self, ctype: str) -> bool:
        """
        Return True if this file is of the type ctype

        ctype: A mime type, can have wildcards like 'image/*'
        """
        predicate = Gio.content_type_is_a
        ctype_guess, uncertain = Gio.content_type_guess(self.object, None)
        ret = predicate(ctype_guess, ctype)
        if ret or not uncertain:
            return ret  # type: ignore

        content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
        gfile = self.get_gfile()
        if not gfile.query_exists(None):
            return False

        info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
        content_type = info.get_attribute_string(content_attr)
        return predicate(content_type, ctype)  # type: ignore

    def _is_good_executable(self):
        if not self._is_executable():
            return False

        ctype, uncertain = Gio.content_type_guess(self.object, None)
        return uncertain or Gio.content_type_can_be_executable(ctype)


class AppLeaf(Leaf):
    def __init__(
        self,
        item: ty.Any = None,
        init_path: ty.Optional[str] = None,
        app_id: ty.Optional[str] = None,
        require_x: bool = True,
    ) -> None:
        """Try constructing an Application for GAppInfo @item,
        for file @path or for package name @app_id.

        @require_x: require executable file
        """
        self.init_item = item
        self.init_path = init_path
        self.init_item_id = app_id and app_id + ".desktop"
        # finish will raise InvalidDataError on invalid item
        self.finish(require_x)
        Leaf.__init__(self, self.object, self.object.get_name())
        self._add_aliases()

    def _add_aliases(self) -> None:
        # find suitable alias
        # use package name: non-extension part of ID
        lowername = str(self).lower()
        package_name = self._get_package_name()
        if package_name and package_name not in lowername:
            self.kupfer_add_alias(package_name)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: ty.Any) -> bool:
        return isinstance(other, type(self)) and self.get_id() == other.get_id()

    def __getstate__(self) -> ty.Dict[str, ty.Any]:
        self.init_item_id = self.object and self.object.get_id()
        state = dict(vars(self))
        state["object"] = None
        state["init_item"] = None
        return state

    def __setstate__(self, state: ty.Dict[str, ty.Any]) -> None:
        vars(self).update(state)
        self.finish()

    def finish(self, require_x: bool = False) -> None:
        """Try to set self.object from init's parameters"""
        item = None
        if self.init_item:
            item = self.init_item
        else:
            # Construct an AppInfo item from either path or item_id
            try:
                if self.init_path and (
                    not require_x or os.access(self.init_path, os.X_OK)
                ):
                    # serilizable if created from a "loose file"
                    self.serializable = 1
                    item = Gio.DesktopAppInfo.new_from_filename(self.init_path)
                elif self.init_item_id:
                    item = Gio.DesktopAppInfo.new(self.init_item_id)

            except TypeError as exc:
                pretty.print_debug(
                    __name__,
                    "Application not found:",
                    self.init_item_id,
                    self.init_path,
                )
                raise InvalidDataError from exc

        self.object = item
        if not self.object:
            raise InvalidDataError

    def repr_key(self) -> ty.Any:
        return self.get_id()

    def _get_package_name(self) -> str:
        return GLib.filename_display_basename(self.get_id())  # type: ignore

    def launch(
        self,
        files: ty.Iterable[str] = (),
        paths: ty.Iterable[str] = (),
        activate: bool = False,
        ctx: ty.Any = None,
    ) -> bool:
        """
        Launch the represented applications

        @files: a seq of GFiles (Gio.File)
        @paths: a seq of bytestring paths
        @activate: activate instead of start new
        """
        try:
            return launch.launch_application(
                self.object,
                files=files,
                paths=paths,
                activate=activate,
                desktop_file=self.init_path,
                screen=ctx and ctx.environment.get_screen(),
            )
        except launch.SpawnError as exc:  # type: ignore
            raise OperationError(exc) from exc

    def get_id(self) -> str:
        """Return the unique ID for this app.

        This is the GIO id "gedit.desktop" minus the .desktop part for
        system-installed applications.
        """
        return launch.application_id(self.object, self.init_path)

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

    def get_description(self) -> ty.Optional[str]:
        # Use Application's description, else use executable
        # for "file-based" applications we show the path
        app_desc = kupferstring.tounicode(self.object.get_description())
        ret = kupferstring.tounicode(app_desc or self.object.get_executable())
        if self.init_path:
            app_path = utils.get_display_path_for_bytestring(self.init_path)
            return f"({app_path}) {ret}"

        return ret

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        return self.object.get_icon()

    def get_icon_name(self) -> str:
        return "exec"


class OpenUrl(Action):
    action_accelerator: ty.Optional[str] = "o"
    rank_adjust: int = 5

    def __init__(self, name: ty.Optional[str] = None) -> None:
        super().__init__(name or _("Open URL"))

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        url = leaf.object
        self.open_url(url)

    def open_url(self, url: str) -> None:
        utils.show_url(url)

    def get_description(self) -> str:
        return _("Open URL with default viewer")

    def get_icon_name(self) -> str:
        return "forward"


class Launch(Action):
    """Launches an application (AppLeaf)"""

    action_accelerator: ty.Optional[str] = "o"
    rank_adjust = 5

    def __init__(
        self,
        name: ty.Optional[str] = None,
        is_running: bool = False,
        open_new: bool = False,
    ) -> None:
        """
        If @is_running, style as if the app is running (Show application)
        If @open_new, always start a new instance.
        """
        Action.__init__(self, name or _("Launch"))
        self.is_running = is_running
        self.open_new = open_new

    def wants_context(self) -> bool:
        return True

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        leaf.launch(activate=not self.open_new, ctx=ctx)

    def get_description(self) -> str:
        if self.is_running:
            return _("Show application window")

        return _("Launch application")

    def get_icon_name(self) -> str:
        if self.is_running:
            return "go-jump"

        return "kupfer-launch"


class LaunchAgain(Launch):
    action_accelerator: ty.Optional[str] = None
    rank_adjust = 0

    def __init__(self, name: ty.Optional[str] = None):
        Launch.__init__(self, name or _("Launch Again"), open_new=True)

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

    def __init__(self):
        Action.__init__(self, _("Close"))

    def activate(
        self, leaf: ty.Any, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> None:
        launch.application_close_all(leaf.get_id())

    def item_types(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield AppLeaf

    def valid_for_item(self, leaf: Leaf) -> bool:
        assert isinstance(leaf, AppLeaf)
        return launch.application_is_running(leaf.get_id())

    def get_description(self) -> str:
        return _("Attempt to close all application windows")

    def get_icon_name(self) -> str:
        return "window-close"


class Open(Action):
    """Open with default application"""

    action_accelerator = "o"
    rank_adjust = 5

    def __init__(self, name=_("Open")):
        Action.__init__(self, name)

    @classmethod
    def default_application_for_leaf(cls, leaf: FileLeaf) -> Gio.AppInfo:
        content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
        gfile = leaf.get_gfile()
        info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
        content_type = info.get_attribute_string(content_attr)
        def_app = Gio.app_info_get_default_for_type(content_type, False)
        if not def_app:
            raise NoDefaultApplicationError(
                (
                    _("No default application for %(file)s (%(type)s)")
                    % {"file": str(leaf), "type": content_type}
                )
                + "\n"
                + _('Please use "%s"') % _("Set Default Application...")
            )

        return def_app

    def wants_context(self) -> bool:
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        self.activate_multiple((leaf,), ctx)

    def activate_multiple(
        self, objects: ty.Iterable[FileLeaf], ctx: ty.Any
    ) -> None:
        appmap: dict[str, Gio.AppInfo] = {}
        leafmap: dict[str, list[FileLeaf]] = {}
        for obj in objects:
            app = self.default_application_for_leaf(obj)
            id_ = app.get_id()
            appmap[id_] = app
            leafmap.setdefault(id_, []).append(obj)

        for id_, leaves in leafmap.items():
            app = appmap[id_]
            launch.launch_application(
                app,
                paths=[L.object for L in leaves],
                activate=False,
                screen=ctx and ctx.environment.get_screen(),
            )

    def get_description(self) -> ty.Optional[str]:
        return _("Open with default application")


class GetParent(Action):
    action_accelerator = "p"
    rank_adjust = -5

    def __init__(self, name=_("Get Parent Folder")):
        super().__init__(name)

    def has_result(self) -> bool:
        return True

    def activate(
        self, leaf: FileLeaf, iobj: ty.Any = None, ctx: ty.Any = None
    ) -> FileLeaf:
        fileloc = leaf.object
        parent = os.path.normpath(os.path.join(fileloc, os.path.pardir))
        return FileLeaf(parent)

    def get_description(self) -> ty.Optional[str]:
        return None

    def get_icon_name(self):
        return "folder-open"


class OpenTerminal(Action):
    action_accelerator = "t"

    def __init__(self, name=_("Open Terminal Here")):
        super().__init__(name)

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        try:
            utils.spawn_terminal(leaf.object, ctx.environment.get_screen())
        except SpawnError as exc:
            raise OperationError(exc) from exc

    def get_description(self) -> ty.Optional[str]:
        return _("Open this location in a terminal")

    def get_icon_name(self):
        return "utilities-terminal"


class Execute(Action):
    """Execute executable file (FileLeaf)"""

    rank_adjust = 10

    def __init__(self, in_terminal=False, quoted=True):
        name = _("Run in Terminal") if in_terminal else _("Run (Execute)")
        super().__init__(name)
        self.in_terminal = in_terminal
        self.quoted = quoted

    def repr_key(self):
        return (self.in_terminal, self.quoted)

    def activate(self, leaf, iobj=None, ctx=None):
        if self.quoted:
            argv = [leaf.object]
        else:
            argv = utils.argv_for_commandline(leaf.object)
        if self.in_terminal:
            utils.spawn_in_terminal(argv)
        else:
            utils.spawn_async(argv)

    def get_description(self) -> ty.Optional[str]:
        if self.in_terminal:
            return _("Run this program in a Terminal")

        return _("Run this program")


class DirectorySource(Source, PicklingHelperMixin, FilesystemWatchMixin):
    def __init__(self, directory: str, show_hidden: bool = False) -> None:
        # Use glib filename reading to make display name out of filenames
        # this function returns a `unicode` object
        name = GLib.filename_display_basename(directory)
        super().__init__(name)
        self.directory = directory
        self.show_hidden = show_hidden
        self.monitor: ty.Any = None

    def __repr__(self) -> str:
        mod = self.__class__.__module__
        cname = self.__class__.__name__
        return (
            f'{mod}.{cname}("{self.directory}", show_hidden={self.show_hidden})'
        )

    def initialize(self) -> None:
        self.monitor = self.monitor_directories(self.directory)

    def finalize(self) -> None:
        self.monitor = None

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        return self.show_hidden or not gfile.get_basename().startswith(".")

    def get_items(self) -> ty.Iterator[Leaf]:
        try:
            for fname in os.listdir(self.directory):
                if not _representable_fname(fname):
                    continue

                if self.show_hidden or not fname.startswith("."):
                    yield ConstructFileLeaf(path.join(self.directory, fname))

        except OSError as exc:
            self.output_error(exc)

    def should_sort_lexically(self) -> bool:
        return True

    def _parent_path(self) -> str:
        return path.normpath(path.join(self.directory, path.pardir))

    def has_parent(self) -> bool:
        return not path.samefile(self.directory, self._parent_path())

    def get_parent(self) -> ty.Optional[DirectorySource]:
        if not self.has_parent():
            return None

        return DirectorySource(self._parent_path())

    def get_description(self) -> str:
        return _("Directory source %s") % self.directory

    def get_gicon(self) -> GdkPixbuf.Pixbuf | None:
        return icons.get_gicon_for_file(self.directory)

    def get_icon_name(self) -> str:
        return "folder"

    def get_leaf_repr(self) -> ty.Optional[Leaf]:
        alias = None
        if os.path.isdir(self.directory) and os.path.samefile(
            self.directory, os.path.expanduser("~")
        ):
            alias = _("Home Folder")

        return FileLeaf(self.directory, alias=alias)

    def provides(self) -> ty.Iterable[ty.Type[Leaf]]:
        yield FileLeaf
        yield AppLeaf


def _representable_fname(fname: str) -> bool:
    "Return False if fname contains surrogate escapes"
    try:
        fname.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


class FileSource(Source):
    def __init__(self, dirlist: ty.List[str], depth: int = 0) -> None:
        """
        @dirlist: Directories as byte strings
        """
        name = GLib.filename_display_basename(dirlist[0])
        if len(dirlist) > 1:
            name = _("%s et. al.") % name

        super().__init__(name)
        self.dirlist = dirlist
        self.depth = depth

    def __repr__(self) -> str:
        mod = self.__class__.__module__
        cname = self.__class__.__name__
        dirs = ", ".join(f'"{d}"' for d in sorted(self.dirlist))
        return f"{mod}.{cname}(({dirs}, ), depth={self.depth})"

    def get_items(self) -> ty.Iterable[Leaf]:
        for directory in self.dirlist:
            files = list(
                utils.get_dirlist(
                    directory, max_depth=self.depth, exclude=self._exclude_file
                )
            )
            yield from map(ConstructFileLeaf, files)

    def should_sort_lexically(self) -> bool:
        return True

    def _exclude_file(self, filename: str) -> bool:
        return filename.startswith(".")

    def get_description(self) -> str:
        return _("Recursive source of %(dir)s, (%(levels)d levels)") % {
            "dir": self.name,
            "levels": self.depth,
        }

    def get_icon_name(self) -> str:
        return "folder-saved-search"

    def provides(self) -> ty.Iterator[ty.Type[Leaf]]:
        yield FileLeaf
        yield AppLeaf
