__kupfer_name__ = _("Thunar")
__kupfer_sources__ = ("ThunarObjects",)
__kupfer_actions__ = (
    "Reveal",
    "GetInfo",
    "SendTo",
    "CopyTo",
    "LinkTo",
    "MoveTo",
)
__description__ = _("File manager Thunar actions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os
from contextlib import suppress
from pathlib import Path

import dbus

from kupfer import config, plugin_support
from kupfer.obj import (
    Action,
    AppLeaf,
    FileLeaf,
    InvalidDataError,
    NoMultiError,
    NotAvailableError,
    RunnableLeaf,
    Source,
)
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.support import pretty

plugin_support.check_dbus_connection()

_SERVICE_NAME = "org.xfce.Thunar"
_OBJECT_PATH = "/org/xfce/FileManager"
_IFACE_NAME = "org.xfce.FileManager"

_TRASH_IFACE_NAME = "org.xfce.Trash"


def _get_thunar():
    """Return the dbus proxy object for Thunar
    we will activate it over d-bus (start if not running)
    """
    bus = dbus.SessionBus()
    try:
        proxy_obj = bus.get_object(_SERVICE_NAME, _OBJECT_PATH)
    except dbus.DBusException as exc:
        pretty.print_error(__name__, exc)
        return None

    iface_obj = dbus.Interface(proxy_obj, _IFACE_NAME)
    return iface_obj


def _get_thunar_trash():
    """Return the dbus proxy object for Thunar
    we will activate it over d-bus (start if not running)
    """
    bus = dbus.SessionBus()
    try:
        proxy_obj = bus.get_object(_SERVICE_NAME, _OBJECT_PATH)
    except dbus.DBusException as exc:
        pretty.print_error(__name__, exc)
        return None

    iface_obj = dbus.Interface(proxy_obj, _TRASH_IFACE_NAME)
    return iface_obj


def _dummy(*args):
    pass


class Reveal(Action):
    def __init__(self):
        Action.__init__(self, _("Select in File Manager"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        gfile = leaf.get_gfile()
        parent = gfile.get_parent()
        if not parent:
            return

        uri = parent.get_uri()
        bname = gfile.get_basename()
        id_ = ctx.environment.get_startup_notification_id()
        display = ctx.environment.get_display()
        try:
            # Thunar 1.2 Uses $DISPLAY and $STARTUP_ID args
            _get_thunar().DisplayFolderAndSelect(
                uri,
                bname,
                display,
                id_,
                reply_handler=_dummy,
                error_handler=_dummy,
            )
        except TypeError:
            # Thunar 1.0 Uses $DISPLAY
            _get_thunar().DisplayFolderAndSelect(
                uri, bname, display, reply_handler=_dummy, error_handler=_dummy
            )

    def item_types(self):
        yield FileLeaf


class GetInfo(Action):
    def __init__(self):
        Action.__init__(self, _("Show Properties"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        gfile = leaf.get_gfile()
        uri = gfile.get_uri()
        id_ = ctx.environment.get_startup_notification_id()
        display = ctx.environment.get_display()
        try:
            # Thunar 1.2 Uses $DISPLAY and $STARTUP_ID args
            _get_thunar().DisplayFileProperties(
                uri, display, id_, reply_handler=_dummy, error_handler=_dummy
            )
        except TypeError:
            # Thunar 1.0 Uses $DISPLAY
            _get_thunar().DisplayFileProperties(
                uri, display, reply_handler=_dummy, error_handler=_dummy
            )

    def item_types(self):
        yield FileLeaf

    def get_description(self):
        return _("Show information about file in file manager")

    def get_icon_name(self):
        return "dialog-information"


class SendTo(Action):
    """Send files to  selected app from "send to" list"""

    def __init__(self):
        Action.__init__(self, _("Send To..."))

    def activate_multiple(self, leaves, iobjs):
        for app in iobjs:
            app.launch(paths=[leaf.object for leaf in leaves])

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        self.activate_multiple((leaf,), (iobj,))

    def item_types(self):
        yield FileLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield AppLeaf

    def object_source(self, for_item=None):
        return _SendToAppsSource()


def _good_destination(dpath: str, spath: str) -> bool:
    """If directory path @dpath is a valid destination for file @spath
    to be copied or moved to.
    """
    if not os.path.isdir(dpath):
        return False

    spath = os.path.normpath(spath)
    dpath = os.path.normpath(dpath)
    cpfx = os.path.commonprefix((spath, dpath))
    return not os.path.samefile(dpath, spath) and cpfx != spath


def leaf_uri(leaf):
    return leaf.get_gfile().get_uri()


class CopyTo(Action, pretty.OutputMixin):
    def __init__(self):
        Action.__init__(self, _("Copy To..."))

    def wants_context(self):
        return True

    def activate_multiple(self, leaves, iobjects, ctx):
        # Unroll by looping over the destinations,
        # copying everything into each destination
        thunar = _get_thunar()
        work_dir = os.path.expanduser("~/")
        display = ctx.environment.get_display()
        notify_id = ctx.environment.get_startup_notification_id()
        sourcefiles = [leaf_uri(L) for L in leaves]

        def _reply(*args):
            self.output_debug("reply got for copying", *args)

        def _reply_error(exc):
            self.output_debug(exc)
            ctx.register_late_error(NotAvailableError(_("Thunar")))

        for dest_iobj in iobjects:
            desturi = leaf_uri(dest_iobj)
            thunar.CopyInto(
                work_dir,
                sourcefiles,
                desturi,
                display,
                notify_id,
                reply_handler=_reply,
                error_handler=_reply_error,
            )

    def activate(self, leaf, iobj=None, ctx=None):
        return self.activate_multiple([leaf], [iobj], ctx)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return True

    def requires_object(self):
        return True

    def object_types(self):
        yield FileLeaf

    def valid_object(self, obj, for_item):
        return _good_destination(obj.object, for_item.object)

    def get_description(self):
        return _("Copy file to a chosen location")


class MoveTo(Action, pretty.OutputMixin):
    def __init__(self):
        Action.__init__(self, _("Move To..."))

    def wants_context(self):
        return True

    def activate_multiple(self, leaves, iobjects, ctx):
        if len(iobjects) != 1:
            raise NoMultiError()

        def _reply():
            self.output_debug("reply got for moving")

        def _reply_error(exc):
            self.output_debug(exc)
            ctx.register_late_error(NotAvailableError(_("Thunar")))

        (dest_iobj,) = iobjects
        # Move everything into the destination
        thunar = _get_thunar()
        if not thunar:
            return

        work_dir = os.path.expanduser("~/")
        display = ctx.environment.get_display()
        notify_id = ctx.environment.get_startup_notification_id()
        sourcefiles = [leaf_uri(L) for L in leaves]
        desturi = leaf_uri(dest_iobj)
        thunar.MoveInto(
            work_dir,
            sourcefiles,
            desturi,
            display,
            notify_id,
            reply_handler=_reply,
            error_handler=_reply_error,
        )

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        assert ctx
        return self.activate_multiple([leaf], [iobj], ctx)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return True

    def requires_object(self):
        return True

    def object_types(self):
        yield FileLeaf

    def valid_object(self, obj, for_item):
        return _good_destination(obj.object, for_item.object)

    def get_description(self):
        return _("Move file to new location")

    def get_icon_name(self):
        return "go-next"


class LinkTo(Action, pretty.OutputMixin):
    def __init__(self):
        Action.__init__(self, _("Symlink In..."))

    def wants_context(self):
        return True

    def activate_multiple(self, leaves, iobjects, ctx):
        # Unroll by looping over the destinations,
        # copying everything into each destination
        thunar = _get_thunar()
        if not thunar:
            return

        work_dir = os.path.expanduser("~/")
        display = ctx.environment.get_display()
        notify_id = ctx.environment.get_startup_notification_id()
        sourcefiles = [leaf_uri(L) for L in leaves]

        def _reply(*args):
            self.output_debug("reply got for copying", *args)

        def _reply_error(exc):
            self.output_debug(exc)
            ctx.register_late_error(NotAvailableError(_("Thunar")))

        for dest_iobj in iobjects:
            desturi = leaf_uri(dest_iobj)
            thunar.LinkInto(
                work_dir,
                sourcefiles,
                desturi,
                display,
                notify_id,
                reply_handler=_reply,
                error_handler=_reply_error,
            )

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        assert ctx
        return self.activate_multiple([leaf], [iobj], ctx)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return True

    def requires_object(self):
        return True

    def object_types(self):
        yield FileLeaf

    def valid_object(self, obj, for_item):
        return _good_destination(obj.object, for_item.object)

    def get_description(self):
        return _("Create a symlink to file in a chosen location")


class EmptyTrash(RunnableLeaf):
    def __init__(self):
        RunnableLeaf.__init__(self, None, _("Empty Trash"))

    def wants_context(self):
        return True

    def run(self, ctx=None):
        assert ctx
        id_ = ctx.environment.get_startup_notification_id()
        thunar = _get_thunar_trash()
        try:
            # Thunar 1.2 Uses $DISPLAY and $STARTUP_ID args
            thunar.EmptyTrash(
                ctx.environment.get_display(),
                id_,
                reply_handler=_dummy,
                error_handler=_dummy,
            )
        except TypeError:
            # Thunar 1.0 uses only $DISPLAY arg
            thunar.EmptyTrash(
                ctx.environment.get_display(),
                reply_handler=_dummy,
                error_handler=_dummy,
            )

    def get_description(self):
        return None

    def get_icon_name(self):
        return "user-trash-full"


class ThunarObjects(AppLeafContentMixin, Source):
    appleaf_content_id = "Thunar"

    def __init__(self):
        Source.__init__(self, _("Thunar"))

    def get_items(self):
        yield EmptyTrash()

    def provides(self):
        yield RunnableLeaf

    def get_icon_name(self):
        return "Thunar"


class _SendToAppsSource(Source):
    """Send To items source"""

    def __init__(self):
        Source.__init__(self, _("Thunar Send To Objects"))

    def get_items(self):
        for data_dir in config.get_data_dirs("sendto", package="Thunar"):
            for filename in os.listdir(data_dir):
                if not filename.endswith(".desktop"):
                    continue

                file_path = Path(data_dir, filename)
                if not file_path.is_file():
                    continue

                with suppress(InvalidDataError):
                    yield AppLeaf(init_path=str(file_path), require_x=False)

    def get_icon_name(self):
        return "Thunar"

    def provides(self):
        yield AppLeaf
