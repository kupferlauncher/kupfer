from __future__ import annotations

import typing as ty
from contextlib import suppress

from gi.repository import GdkPixbuf, Gio, Gtk
from gi.repository.Gio import (
    FILE_ATTRIBUTE_STANDARD_ICON,
    FILE_ATTRIBUTE_THUMBNAIL_PATH,
    File,
    FileIcon,
    Icon,
    ThemedIcon,
)
from gi.repository.GLib import GError

from kupfer.core import settings
from kupfer.support import datatools, pretty, scheduler

_ICON_CACHE: ty.Final[dict[int, datatools.LruCache[str, GdkPixbuf.Pixbuf]]] = {}
# number of elements in icon lru cache (per icon size)
_ICON_CACHE_SIZE_LARGE = 15
_ICON_CACHE_SIZE = 64

_LARGE_SZ = 128
_SMALL_SZ = 24

## default fallbacks for our themable icons
_KUPFER_ICON_FALLBACKS: ty.Final = {
    "kupfer-execute": "system-run",
    "kupfer-object": "text-x-generic",
    "kupfer-object-multiple": "folder",
    "kupfer-catalog": "system-search",
    "kupfer-search": "system-search",
}

_KUPFER_LOCALLY_INSTALLED_NAMES: ty.Final[set[str]] = set()

# keep missing files to prevent try to load every time
_MISSING_ICON_FILES: ty.Final[set[str]] = set()


def _icon_theme_changed(theme):
    pretty.print_info(__name__, "Icon theme changed, clearing cache")
    _ICON_CACHE.clear()


_default_theme = Gtk.IconTheme.get_default()  # pylint: disable=no-member
_default_theme.connect("changed", _icon_theme_changed)
_local_theme = Gtk.IconTheme.new()
_local_theme.set_search_path([])


def parse_load_icon_list(
    icon_list_data: bytes,
    get_data_func: ty.Callable[[str], bytes],
    plugin_name: str | None = None,
) -> None:
    """
    @icon_list_data: A bytestring whose lines identify icons
    @get_data_func: A function to return the data for a relative filename
    @plugin_name: plugin id, if applicable
    """
    try:
        icon_list_string = icon_list_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        pretty.print_error(
            __name__,
            f"Malformed icon-list in plugin {plugin_name!r}: {exc!r}",
        )
        raise

    for line in icon_list_string.splitlines():
        # ignore '#'-comments
        if line.startswith("#") or not line.strip():
            continue

        fields = tuple(map(str.strip, line.split("\t", 2)))
        if len(fields) < 2:
            pretty.print_error(
                __name__,
                "Malformed icon-list line {line!r} from {plugin_name!r}",
            )
            continue

        icon_name, basename, *_tail = fields
        override = "!override" in fields
        _load_icon_from_func(
            plugin_name, icon_name, get_data_func, override, func_args=basename
        )


def _load_icon_from_func(
    plugin_name: str | None,
    icon_name: str,
    get_data_func: ty.Callable[[str], bytes],
    override: bool,
    func_args: str,
) -> None:
    """
    Load icon from @icon_data into the name @icon_name

    @get_data_func: function to retrieve the data if needed
    @override: override the icon theme
    """
    if not override and icon_name in _KUPFER_LOCALLY_INSTALLED_NAMES:
        pretty.print_debug(__name__, "Skipping existing", icon_name)
        return

    if not override and _default_theme.has_icon(icon_name):
        pretty.print_debug(__name__, "Skipping themed icon", icon_name)
        return

    try:
        icon_data = get_data_func(func_args)
    except Exception:
        pretty.print_error(
            __name__, f"Error loading icon {icon_name!r} for {plugin_name!r}"
        )
        pretty.print_exc(__name__)
        return

    for size in (_SMALL_SZ, _LARGE_SZ):
        pixbuf = get_pixbuf_from_data(icon_data, size, size)
        Gtk.IconTheme.add_builtin_icon(  # pylint: disable=no-member
            icon_name, size, pixbuf
        )
        pretty.print_debug(
            __name__, "Loading icon", icon_name, "at", size, "for", plugin_name
        )

    _KUPFER_LOCALLY_INSTALLED_NAMES.add(icon_name)


def get_icon(key: str, icon_size: int) -> ty.Iterator[GdkPixbuf.Pixbuf]:
    """
    try retrieve icon in cache
    is a generator so it can be concisely called with a for loop
    """
    try:
        rec = _ICON_CACHE[icon_size][key]
    except KeyError:
        return

    yield rec


def store_icon(key: str, icon_size: int, icon: GdkPixbuf.Pixbuf) -> None:
    """
    Store an icon in cache. It must not have been stored before
    """
    assert icon, f"icon {key} may not be {icon}"
    if icon_size not in _ICON_CACHE:
        cache_size = _ICON_CACHE_SIZE
        if icon_size == _LARGE_SZ:
            cache_size = _ICON_CACHE_SIZE_LARGE

        _ICON_CACHE[icon_size] = datatools.LruCache(cache_size)

    _ICON_CACHE[icon_size][key] = icon


def _get_icon_dwim(
    icon: ty.Union[Icon, str], icon_size: int
) -> GdkPixbuf.Pixbuf | None:
    """Make an icon at @icon_size where
    @icon can be either an icon name, or a gicon
    """
    if isinstance(icon, Icon):
        return get_icon_for_gicon(icon, icon_size)

    if icon:
        return get_icon_for_name(icon, icon_size)

    return None


# pylint: disable=too-few-public-methods
class ComposedIcon:
    """
    A composed icon, which kupfer will render to pixbuf as
    background icon with the decorating icon as emblem
    """

    def __init__(
        self,
        baseicon: GIcon | str,
        emblem: GIcon | str,
        emblem_is_fallback: bool = False,
    ) -> None:
        self.minimum_icon_size = 48
        self.baseicon = baseicon
        self.emblemicon = emblem

    @classmethod
    def new(cls, *args, **kwargs):
        """Contstuct a composed icon from @baseicon and @emblem,
        which may be GIcons or icon names (strings)
        """
        return cls(*args, **kwargs)


# pylint: disable=invalid-name
def ComposedIconSmall(
    baseicon: GIcon | str, emblem: GIcon | str, **kwargs: ty.Any
) -> ComposedIcon:
    """Create composed icon for leaves with emblem visible on browser list"""
    icon = ComposedIcon(baseicon, emblem, **kwargs)
    icon.minimum_icon_size = _SMALL_SZ
    return icon


GIcon = ty.Union[ComposedIcon, ThemedIcon, FileIcon]


def _render_composed_icon(
    composed_icon: ComposedIcon, icon_size: int
) -> GdkPixbuf.Pixbuf | None:
    # If it's too small, render as fallback icon
    if icon_size < composed_icon.minimum_icon_size:
        return _get_icon_for_standard_gicon(composed_icon.baseicon, icon_size)

    emblemicon = composed_icon.emblemicon
    baseicon = composed_icon.baseicon
    toppbuf = _get_icon_dwim(emblemicon, icon_size)
    bottompbuf = _get_icon_dwim(baseicon, icon_size)
    if not toppbuf or not bottompbuf:
        return None

    dest = bottompbuf.copy()
    # @frac is the scale
    frac = 0.6
    dcoord = int((1 - frac) * icon_size)
    dsize = int(frac * icon_size)
    # http://library.gnome.org/devel/gdk-pixbuf/unstable//gdk-pixbuf-scaling.html
    toppbuf.composite(
        dest,
        dcoord,
        dcoord,
        dsize,
        dsize,
        dcoord,
        dcoord,
        frac,
        frac,
        GdkPixbuf.InterpType.BILINEAR,
        255,
    )
    return dest


def get_thumbnail_for_gfile(
    gfile: Gio.File, width: int = -1, height: int = -1
) -> GdkPixbuf.Pixbuf | None:
    """
    Return a Pixbuf thumbnail for the file at
    gfile: Gio.File
    size is @width x @height

    return None if not found
    """
    if not gfile.query_exists():
        return None

    finfo = gfile.query_info(
        FILE_ATTRIBUTE_THUMBNAIL_PATH, Gio.FileQueryInfoFlags.NONE, None
    )
    thumb_path = finfo.get_attribute_byte_string(FILE_ATTRIBUTE_THUMBNAIL_PATH)

    return get_pixbuf_from_file(thumb_path, width, height)


def get_pixbuf_from_file(
    thumb_path: str | None, width: int = -1, height: int = -1
) -> GdkPixbuf.Pixbuf | None:
    """
    Return a Pixbuf thumbnail for the file at @thumb_path
    sized @width x @height
    For non-icon pixbufs:
    We might cache these, but on different terms than the icon cache
    if @thumb_path is None, return None
    """
    if not thumb_path:
        return None
    try:
        icon = GdkPixbuf.Pixbuf.new_from_file_at_size(thumb_path, width, height)
        return icon
    except GError as exc:
        # this error is not important, the program continues on fine,
        # so we put it in debug output.
        pretty.print_debug(
            __name__, "get_pixbuf_from_file file:", thumb_path, "error:", exc
        )

    return None


def get_gicon_for_file(uri: str) -> GIcon | None:
    """
    Return a GIcon representing the file at
    the @uri, which can be *either* and uri or a path

    return None if not found
    """

    if uri in _MISSING_ICON_FILES:
        return None

    gfile = File.new_for_path(uri)
    if not gfile.query_exists():
        gfile = File.new_for_uri(uri)
        if not gfile.query_exists():
            _MISSING_ICON_FILES.add(uri)
            return None

    finfo = gfile.query_info(
        FILE_ATTRIBUTE_STANDARD_ICON, Gio.FileQueryInfoFlags.NONE, None
    )
    gicon = finfo.get_attribute_object(FILE_ATTRIBUTE_STANDARD_ICON)
    return gicon


def get_gicon_from_file(path: str) -> FileIcon | None:
    """Load GIcon from @path; return None if failed."""
    file = File.new_for_path(path)
    if file.query_exists():
        return FileIcon.new(file)

    return None


def get_icon_for_gicon(gicon: GIcon, icon_size: int) -> GdkPixbuf.Pixbuf | None:
    """
    Return a pixbuf of @icon_size for the @gicon

    NOTE: Currently only the following can be rendered:
        Gio.ThemedIcon
        Gio.FileIcon
        kupfer.icons.ComposedIcon
    """
    # FIXME: We can't load any general GIcon
    if not gicon:
        return None

    if isinstance(gicon, ComposedIcon):
        return _render_composed_icon(gicon, icon_size)

    return _get_icon_for_standard_gicon(gicon, icon_size)


def _get_icon_for_standard_gicon(
    gicon: ty.Any, icon_size: int
) -> GdkPixbuf.Pixbuf | None:
    """Render ThemedIcon and FileIcon"""
    if isinstance(gicon, FileIcon):
        ifile = gicon.get_file()
        return get_icon_from_file(ifile.get_path(), icon_size)

    if isinstance(gicon, ThemedIcon):
        names = gicon.get_names()
        return get_icon_for_name(names[0], icon_size, names)

    pretty.print_debug(
        __name__, "_get_icon_for_standard_gicon, could not load", gicon
    )
    return None


class IconRenderer:
    """
    Default GTK+ implementation
    """

    @classmethod
    def pixbuf_for_name(
        cls, icon_name: str, icon_size: int
    ) -> GdkPixbuf.Pixbuf | None:
        if icon_name in _KUPFER_LOCALLY_INSTALLED_NAMES:
            with suppress(GError):
                return _local_theme.load_icon(
                    icon_name,
                    icon_size,
                    Gtk.IconLookupFlags.USE_BUILTIN  # pylint: disable=no-member
                    | Gtk.IconLookupFlags.FORCE_SIZE,  # pylint: disable=no-member
                )

        with suppress(GError):
            return _default_theme.load_icon(
                icon_name,
                icon_size,
                Gtk.IconLookupFlags.USE_BUILTIN  # pylint: disable=no-member
                | Gtk.IconLookupFlags.FORCE_SIZE,  # pylint: disable=no-member
            )

        return None

    @classmethod
    def pixbuf_for_file(
        cls, file_path: str, icon_size: int
    ) -> GdkPixbuf.Pixbuf | None:
        try:
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                file_path, icon_size, icon_size
            )
            return icon

        except GError:
            pretty.print_exc(__name__)

        return None


_ICON_RENDERER = IconRenderer  # pylint: disable=invalid-name


def _setup_icon_renderer(_sched: ty.Any) -> None:
    setctl = settings.get_settings_controller()
    setctl.connect("alternatives-changed::icon_renderer", _icon_render_change)
    setctl.connect("value-changed::tools.icon_renderer", _icon_render_change)
    _icon_render_change(setctl)


def _icon_render_change(setctl, *_arguments):
    global _ICON_RENDERER  # pylint: disable=global-statement
    renderer_dict = setctl.get_preferred_alternative("icon_renderer")
    renderer = renderer_dict.get("renderer")
    if not renderer or renderer is _ICON_RENDERER:
        return

    pretty.print_debug(__name__, "Using", renderer)
    _icon_theme_changed(None)
    _ICON_RENDERER = renderer


scheduler.get_scheduler().connect("loaded", _setup_icon_renderer)


def get_icon_for_name(
    icon_name: str,
    icon_size: int,
    icon_names: ty.Iterable[str] | None = None,
) -> GdkPixbuf.Pixbuf | None:
    with suppress(KeyError):
        return _ICON_CACHE[icon_size][icon_name]

    # Try the whole list of given names
    for load_name in icon_names or (icon_name,):
        try:
            if icon := _ICON_RENDERER.pixbuf_for_name(load_name, icon_size):
                break

            if fallback_name := _KUPFER_ICON_FALLBACKS.get(icon_name):
                if icon := _ICON_RENDERER.pixbuf_for_name(
                    fallback_name, icon_size
                ):
                    break

        except Exception:
            pretty.print_exc(__name__)
            icon = None
    else:
        # if we did not reach 'break' in the loop
        return None
    # We store the first icon in the list, even if the match
    # found was later in the chain
    store_icon(icon_name, icon_size, icon)
    return icon


def get_icon_from_file(
    icon_file: str, icon_size: int
) -> GdkPixbuf.Pixbuf | None:
    # try to load from cache
    with suppress(KeyError):
        return _ICON_CACHE[icon_size][icon_file]

    if icon_file in _MISSING_ICON_FILES:
        return None

    if icon := _ICON_RENDERER.pixbuf_for_file(icon_file, icon_size):
        store_icon(icon_file, icon_size, icon)
        return icon

    _MISSING_ICON_FILES.add(icon_file)
    return None


def is_good(gicon: GIcon | None) -> bool:
    """Return True if it is likely that @gicon will load a visible icon
    (icon name exists in theme, or icon references existing file)
    """
    if not gicon:
        return False

    if isinstance(gicon, ThemedIcon):
        return bool(get_good_name_for_icon_names(gicon.get_names()))

    if isinstance(gicon, FileIcon):
        ifile = gicon.get_file()
        return ifile.query_exists()  # type: ignore

    # Since we can't load it otherwise (right now, see above)
    return False


def get_gicon_with_fallbacks(
    gicon: GIcon | None, names: ty.Iterable[str]
) -> GIcon | None:
    if is_good(gicon):
        return gicon

    name = None
    for name in names:
        gicon = ThemedIcon.new(name)
        if is_good(gicon):
            return gicon

    return ThemedIcon.new(name) if name else None


def get_good_name_for_icon_names(names: ty.Iterable[str]) -> str | None:
    """Return first name in @names that exists
    in current icon theme, or None
    """
    for name in names:
        if _default_theme.has_icon(name):
            return name

    return None


def get_gicon_for_names(*names: str) -> ThemedIcon:
    return ThemedIcon.new_from_names(names)


def get_pixbuf_from_data(
    data: bytes,
    width: int | None = None,
    height: int | None = None,
) -> GdkPixbuf.Pixbuf:
    """Create pixbuf object from data with optional scaling

    @data: picture as raw data
    @width, @heigh: optional destination size
    """

    ploader = GdkPixbuf.PixbufLoader.new()

    if width and height:

        def set_size(
            img: GdkPixbuf.PixbufLoader, img_width: int, img_height: int
        ) -> None:
            assert width and height
            scale = min(width / float(img_width), height / float(img_height))
            new_width, new_height = int(img_width * scale), int(
                img_height * scale
            )
            img.set_size(new_width, new_height)

        ploader.connect("size-prepared", set_size)

    ploader.write(data)
    ploader.close()
    return ploader.get_pixbuf()
