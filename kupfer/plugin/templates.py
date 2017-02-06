__kupfer_name__ = _("Document Templates")
__kupfer_sources__ = ("TemplatesSource", )
__kupfer_actions__ = ("CreateNewDocument", )
__description__ = _("Create new documents from your templates")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import os

from gi.repository import Gio, GLib

from kupfer.objects import Leaf, Action, Source, FileLeaf
from kupfer import icons, utils, pretty
from kupfer.obj import helplib
from kupfer.obj.helplib import FilesystemWatchMixin

DEFAULT_TMPL_DIR = "~/Templates"

class Template (FileLeaf):
    def __init__(self, path):
        basename = GLib.filename_display_basename(path)
        nameroot, ext = os.path.splitext(basename)
        FileLeaf.__init__(self, path, _("%s template") % nameroot)

    def get_actions(self):
        yield CreateDocumentIn()
        for a in FileLeaf.get_actions(self):
            yield a

    def get_gicon(self):
        file_gicon = FileLeaf.get_gicon(self)
        return icons.ComposedIcon("text-x-generic-template", file_gicon)

class EmptyFile (Leaf):
    def __init__(self):
        Leaf.__init__(self, None, _("Empty File"))
    def repr_key(self):
        return ""
    def get_actions(self):
        yield CreateDocumentIn()
    def get_icon_name(self):
        return "text-x-generic"

class NewFolder (Leaf):
    def __init__(self):
        Leaf.__init__(self, None, _("New Folder"))
    def repr_key(self):
        return ""
    def get_actions(self):
        yield CreateDocumentIn()
    def get_icon_name(self):
        return "folder"

class CreateNewDocument (Action):
    def __init__(self):
        Action.__init__(self, _("Create New Document..."))

    def has_result(self):
        return True
    def activate(self, leaf, iobj):
        if iobj.object is not None:
            # Copy the template to destination directory
            basename = os.path.basename(iobj.object)
            tmpl_gfile = Gio.File.new_for_path(iobj.object)
            destpath = utils.get_destpath_in_directory(leaf.object, basename)
            destfile = Gio.File.new_for_path(destpath)
            tmpl_gfile.copy(destfile, Gio.FileCopyFlags.ALL_METADATA, None, None, None)
        elif isinstance(iobj, NewFolder):
            filename = str(iobj)
            destpath = utils.get_destpath_in_directory(leaf.object, filename)
            os.makedirs(destpath)
        else:
            # create new empty file
            filename = str(iobj)
            f, destpath = utils.get_destfile_in_directory(leaf.object, filename)
            f.close()
        return FileLeaf(destpath)

    def item_types(self):
        yield FileLeaf
    def valid_for_item(self, leaf):
        return leaf.is_dir()

    def requires_object(self):
        return True
    def object_types(self):
        yield Template
        yield EmptyFile
        yield NewFolder

    def object_source(self, for_item=None):
        return TemplatesSource()

    def get_description(self):
        return _("Create a new document from template")
    def get_icon_name(self):
        return "document-new"

class CreateDocumentIn(helplib.reverse_action(CreateNewDocument)):
    rank_adjust = 10
    def __init__(self):
        Action.__init__(self, _("Create Document In..."))

class TemplatesSource (Source, FilesystemWatchMixin):
    def __init__(self):
        Source.__init__(self, _("Document Templates"))

    @classmethod
    def _get_tmpl_dir(self):
        tmpl_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_TEMPLATES)
        if tmpl_dir == os.path.expanduser("~"):
            tmpl_dir = None
        if not tmpl_dir:
            tmpl_dir = os.path.expanduser(DEFAULT_TMPL_DIR)
        pretty.print_debug(__name__, tmpl_dir)
        return tmpl_dir

    def initialize(self):
        self.monitor_token = self.monitor_directories(self._get_tmpl_dir())

    def get_items(self):
        tmpl_dir = self._get_tmpl_dir()
        yield EmptyFile()
        yield NewFolder()
        try:
            for fname in os.listdir(tmpl_dir):
                yield Template(os.path.join(tmpl_dir, fname))
        except EnvironmentError as exc:
            self.output_error(exc)

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return None
    def get_icon_name(self):
        return "system-file-manager"

    def provides(self):
        yield Template

