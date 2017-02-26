__kupfer_name__ = _("Trash")
__kupfer_actions__ = ("MoveToTrash", "EmptyTrash")
__kupfer_sources__ = ("TrashSource", )
__description__ = _("Access trash contents")
__version__ = "2017.2"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

from gi.repository import Gio, GLib

from kupfer.objects import Leaf, Action, Source, SourceLeaf, FileLeaf
from kupfer.objects import OperationError
from kupfer.obj.fileactions import Open
from kupfer import utils, icons, pretty


TRASH_URI = 'trash://'

class MoveToTrash (Action):
    # this should never be default
    rank_adjust = -10
    def __init__(self):
        Action.__init__(self, _("Move to Trash"))

    def activate(self, leaf):
        gfile = leaf.get_gfile()
        try:
            gfile.trash()
        except GLib.Error as exc:
            raise OperationError(exc.message)

    def valid_for_item(self, item):
        gfile = item.get_gfile()
        if not gfile.query_exists(None):
            return False
        info = gfile.query_info(Gio.FILE_ATTRIBUTE_ACCESS_CAN_TRASH,
                Gio.FileQueryInfoFlags.NONE, None)
        return info.get_attribute_boolean(Gio.FILE_ATTRIBUTE_ACCESS_CAN_TRASH)
    def get_description(self):
        return _("Move this file to trash")
    def get_icon_name(self):
        return "user-trash-full"
    def item_types(self):
        yield FileLeaf


class RestoreTrashedFile (Action):
    def __init__(self):
        Action.__init__(self, _("Restore"))

    def has_result(self):
        return True

    def activate(self, leaf):
        orig_path = leaf.get_orig_path()
        if not orig_path:
            return
        orig_gfile = Gio.File.new_for_path(orig_path)
        cur_gfile = leaf.get_gfile()
        if orig_gfile.query_exists():
            raise OperationError("Target file exists at %s" % orig_gfile.get_path())
        pretty.print_debug(__name__, "Move %s to %s" % (cur_gfile, orig_gfile))
        ret = cur_gfile.move(orig_gfile, Gio.FileCopyFlags.ALL_METADATA, None, None, None)
        pretty.print_debug(__name__, "Move ret=%s" % (ret, ))
        return FileLeaf(orig_gfile.get_path())

    def get_description(self):
        return _("Move file back to original location")
    def get_icon_name(self):
        return "edit-undo"

class EmptyTrash (Action):
    rank_adjust = -1
    def __init__(self):
        Action.__init__(self, _("Empty Trash"))
    def activate(self, trash):
        gfile = Gio.File.new_for_uri(TRASH_URI)
        failed = []
        for info in gfile.enumerate_children("standard::*,trash::*",
                Gio.FileQueryInfoFlags.NONE, None):
            name = info.get_name()
            if not gfile.get_child(name).delete():
                failed.append(name)
        if failed:
            err = _("Could not delete files:\n    ")
            raise OperationError(err + '\n    '.join(failed))
    def get_icon_name(self):
        return "user-trash-full"

class TrashFile (Leaf):
    """A file in the trash. Represented object is a file info object"""
    def __init__(self, trash_uri, info):
        name = info.get_display_name()
        Leaf.__init__(self, info, name)
        self._trash_uri = trash_uri
    def get_actions(self):
        if self.get_orig_path():
            yield RestoreTrashedFile()
    def get_gfile(self):
        cur_gfile = Gio.File.new_for_uri(self._trash_uri).get_child(self.object.get_name())
        return cur_gfile
    def get_orig_path(self):
        try:
            orig_path = self.object.get_attribute_byte_string("trash::orig-path")
            return orig_path
        except AttributeError:
            pass
        return None

    def is_valid(self):
        return self.get_gfile().query_exists()

    def get_description(self):
        orig_path = self.get_orig_path()
        return utils.get_display_path_for_bytestring(orig_path) if orig_path \
                else None
    def get_gicon(self):
        return self.object.get_icon()
    def get_icon_name(self):
        return "text-x-generic"

class TrashContentSource (Source):
    def __init__(self, trash_uri, name):
        Source.__init__(self, name)
        self._trash_uri = trash_uri

    def is_dynamic(self):
        return True
    def get_items(self):
        gfile = Gio.File.new_for_uri(self._trash_uri)
        for info in gfile.enumerate_children("standard::*,trash::*",
                Gio.FileQueryInfoFlags.NONE, None):
            yield TrashFile(self._trash_uri, info)
    def should_sort_lexically(self):
        return True
    def get_gicon(self):
        return icons.get_gicon_for_file(self._trash_uri)

class SpecialLocation (Leaf):
    """ Base class for Special locations (in GIO/GVFS),
    such as trash:/// Here we assume they are all "directories"
    """
    def __init__(self, location, name=None, description=None, icon_name=None):
        """Special location with @location and
        @name. If unset, we find @name from filesystem
        @description is Leaf description"""
        gfile = Gio.File.new_for_uri(location)
        info = gfile.query_info(Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME,
                Gio.FileQueryInfoFlags.NONE, None)
        name = (info.get_attribute_string(Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME) or location)
        Leaf.__init__(self, location, name)
        self.description = description
        self.icon_name = icon_name
    def get_actions(self):
        yield OpenTrash()
    def get_description(self):
        return self.description or self.object
    def get_gicon(self):
        # Get icon
        return icons.get_gicon_for_file(self.object)
    def get_icon_name(self):
        return "folder"

class Trash (SpecialLocation):
    def __init__(self, trash_uri, name=None):
        SpecialLocation.__init__(self, trash_uri, name=name)

    def has_content(self):
        return self.get_item_count()
    def content_source(self, alternate=False):
        return TrashContentSource(self.object, name=str(self))

    def get_actions(self):
        for action in SpecialLocation.get_actions(self):
            yield action
        if self.get_item_count():
            yield EmptyTrash()

    def get_item_count(self):
        gfile = Gio.File.new_for_uri(self.object)
        info = gfile.query_info(Gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT,
                Gio.FileQueryInfoFlags.NONE, None)
        return info.get_attribute_uint32(Gio.FILE_ATTRIBUTE_TRASH_ITEM_COUNT)

    def get_description(self):
        item_count = self.get_item_count()
        if not item_count:
            return _("Trash is empty")
        # proper translation of plural
        return ngettext("Trash contains one file",
            "Trash contains %(num)s files", item_count) % {"num": item_count}

class InvisibleSourceLeaf (SourceLeaf):
    """Hack to hide this source"""
    def is_valid(self):
        return False

class TrashSource (Source):
    def __init__(self):
        Source.__init__(self, _("Trash"))
    def get_items(self):
        try:
            yield Trash(TRASH_URI)
        except GLib.Error as exc:
            self.output_exc()
    def get_leaf_repr(self):
        return InvisibleSourceLeaf(self)
    def provides(self):
        yield SpecialLocation
    def get_icon_name(self):
        return "user-trash"

class OpenTrash(Open):
    def activate(self, obj, ctx=None):
        utils.show_url(obj.object)

