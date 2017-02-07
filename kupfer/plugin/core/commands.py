__kupfer_actions__ = ("SaveToFile", )

import os

from kupfer.objects import Action, FileLeaf, TextLeaf, TextSource
from kupfer.obj.compose import ComposedLeaf
from kupfer.core import execfile


class SaveToFile (Action):
    def __init__(self):
        Action.__init__(self, _("Save As..."))

    def has_result(self):
        return True

    def activate(self, obj, iobj):
        filepath = iobj.object
        execfile.save_to_file(obj, filepath)
        execfile.update_icon(obj, iobj.object)
        return FileLeaf(os.path.abspath(filepath))

    def item_types(self):
        yield ComposedLeaf

    def requires_object(self):
        return True
    def object_types(self):
        yield TextLeaf
    def object_source(self, for_item=None):
        return NameSource(_("Save As..."), ".kfcom")

class NameSource (TextSource):
    """A source for new names for a file;
    here we "autopropose" the source file's extension,
    but allow overriding it as well as renaming to without
    extension (selecting the normal TextSource-returned string).
    """
    def __init__(self, name, extension, sourcefile=None):
        TextSource.__init__(self, name)
        self.sourcefile = sourcefile
        self.extension = extension

    def get_rank(self):
        return 100

    def get_items(self, text):
        if not text:
            return
        t_root, t_ext = os.path.splitext(text)
        yield TextLeaf(text) if t_ext else TextLeaf(t_root + self.extension)

    def get_gicon(self):
        return self.sourcefile and self.sourcefile.get_gicon()

    def get_icon_name(self):
        return "text-x-generic"

