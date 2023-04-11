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
    "CopyContent",
)
__description__ = _("Action for text files")
__version__ = "2017.1"
__author__ = ""

from pathlib import Path

from gi.repository import Gdk, Gtk

from kupfer.obj import Action, FileLeaf, TextLeaf, helplib
from kupfer.support import fileutils, kupferstring, validators


class AppendTo(Action):
    def __init__(self, name=None):
        super().__init__(name or _("Append To..."))

    def activate(self, leaf, iobj=None, ctx=None):
        with open(
            iobj.object, "at", encoding=kupferstring.get_encoding()
        ) as outfile:
            outfile.write(leaf.object)
            outfile.write("\n")

    def item_types(self):
        yield TextLeaf

    def requires_object(self):
        return True

    def object_types(self):
        yield FileLeaf

    def valid_object(self, iobj, for_item=None):
        # K: allow select all writable FileLeaves; filtering by content
        # prevent navigate between directories
        return iobj.is_writable()
        # return iobj.is_content_type("text/plain")

    def get_icon_name(self):
        return "list-add"


class AppendText(helplib.reverse_action(AppendTo)):  # type: ignore
    def __init__(self):
        super().__init__(_("Append..."))


class WriteTo(Action):
    def __init__(self):
        super().__init__(_("Write To..."))

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj

        if isinstance(iobj, TextLeaf):
            outfile, outpath = fileutils.get_destfile(iobj.object)
        elif isinstance(iobj, FileLeaf):
            outfile, outpath = fileutils.get_destfile_in_directory(
                iobj.object, _("Empty File")
            )
        else:
            raise ValueError()

        if not outfile or not outpath:
            return None

        try:
            text = str(leaf.object).encode()
            outfile.write(text)
            if not text.endswith(b"\n"):
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
        yield TextLeaf

    def valid_object(self, iobj, for_item=None):
        if isinstance(iobj, FileLeaf):
            return iobj.is_dir()

        # we accept TextLeaf if it look like path
        path_str = str(iobj.object)
        if not validators.is_valid_file_path(path_str):
            return False

        path = Path(path_str)
        # file should not exist
        if path.exists():
            return False

        # but parent dir must exists and be writable
        return fileutils.is_directory_writable(path.parent)

    def get_description(self):
        return _("Write the text to a new file in specified directory")

    def get_icon_name(self):
        return "document-new"


class GetTextContents(Action):
    def __init__(self):
        super().__init__(_("Get Text Contents"))

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        text = Path(leaf.object).read_text(encoding=kupferstring.get_encoding())
        return TextLeaf(text)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return leaf.is_content_type("text/plain")

    def get_icon_name(self):
        return "edit-copy"


class CopyContent(Action):
    action_accelerator = "c"

    def __init__(self):
        super().__init__(_("Copy content"))

    def has_result(self):
        return True

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return leaf.is_content_type("text/plain")

    def get_icon_name(self):
        return "edit-copy"

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        self.activate_multiple((leaf,), ctx=ctx)

    def activate_multiple(self, objs, iobjects=None, ctx=None):
        assert ctx

        clip = Gtk.Clipboard.get_for_display(
            ctx.environment.get_screen().get_display(), Gdk.SELECTION_CLIPBOARD
        )

        content = []
        for obj in objs:
            try:
                content.append(
                    Path(obj.object).read_text(
                        encoding=kupferstring.get_encoding()
                    )
                )
            except Exception as err:
                content.append(f"Read file {obj.object} error: {err}")

        clip.set_text("\n".join(content), -1)  # -1 for computed string length

    def get_description(self):
        return _("Copy file content to clipboard")
