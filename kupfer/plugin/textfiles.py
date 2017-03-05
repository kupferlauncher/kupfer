"""
Work with Textfiles: Allow appending and writing new files,
or extracting the content of files.

All Text in Kupfer is in unicode. When we read from textfiles or write
to textfiles, we always work in the locale-defined encoding.

FIXME: Be less strict (use UTF-8 if locale says Ascii)
"""



__kupfer_name__ = _("Textfiles")
__kupfer_actions__ = (
        "AppendTo",
        "AppendText",
        "WriteTo",
        "GetTextContents",
    )
__description__ = None
__version__ = "2017.1"
__author__ = ""

from gi.repository import Gio

from kupfer.objects import Action
from kupfer.objects import TextLeaf, FileLeaf
from kupfer.obj import helplib
from kupfer import kupferstring
from kupfer import utils

# FIXME: Sometimes require that the type is *exactly* text/plain?

class AppendTo (Action):
    def __init__(self, name=None):
        if not name:
            name = _("Append To...")
        Action.__init__(self, name)

    def activate(self, leaf, iobj):
        with open(iobj.object, "a") as outfile:
            outfile.write(leaf.object)
            outfile.write("\n")

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True
    def object_types(self):
        yield FileLeaf
    def valid_object(self, iobj, for_item=None):
        return iobj.is_content_type("text/plain")

    def get_icon_name(self):
        return "list-add"

class AppendText (helplib.reverse_action(AppendTo)):
    def __init__(self):
        Action.__init__(self, _("Append..."))

class WriteTo (Action):
    def __init__(self):
        Action.__init__(self, _("Write To..."))

    def has_result(self):
        return True

    def activate(self, leaf, iobj):
        outfile, outpath = \
                utils.get_destfile_in_directory(iobj.object, _("Empty File"))
        try:
            l_text = kupferstring.tolocale(leaf.object)
            outfile.write(l_text)
            if not l_text.endswith(b"\n"):
                outfile.write(b"\n")
        finally:
            outfile.close()
        return FileLeaf(outpath)

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True
    def object_types(self):
        yield FileLeaf
    def valid_object(self, iobj, for_item=None):
        return iobj.is_dir()

    def get_description(self):
        return _("Write the text to a new file in specified directory")

    def get_icon_name(self):
        return "document-new"

class GetTextContents (Action):
    def __init__(self):
        Action.__init__(self, _("Get Text Contents"))

    def has_result(self):
        return True

    def activate(self, leaf):
        with open(leaf.object, "rb") as infile:
            l_text = infile.read()
            us_text = kupferstring.fromlocale(l_text)
        return TextLeaf(us_text)

    def item_types(self):
        yield FileLeaf
    def valid_for_item(self, item):
        return item.is_content_type("text/plain")

    def get_icon_name(self):
        return "edit-copy"
