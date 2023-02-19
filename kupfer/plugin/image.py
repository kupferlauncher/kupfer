__kupfer_name__ = _("Image Tools")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
    "Scale",
    "Rotate90",
    "Rotate270",
    "Autorotate",
)
__description__ = _(
    "Image transformation tools using 'convert' from ImageMagick"
)
__version__ = "2017.1"
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import typing as ty
import subprocess
from contextlib import suppress

# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer import runtimehelper, utils
from kupfer.obj import Action, FileLeaf, OperationError, TextLeaf
from kupfer.support import pretty
from kupfer.desktop_launch import SpawnError

if ty.TYPE_CHECKING:
    _ = str

# TODO: use imagemagick -auto-orient ??


def _spawn_operation_err(argv):
    try:
        utils.spawn_async_raise(argv)
    except SpawnError as exc:
        raise OperationError(exc.args[0].message) from exc


class Scale(Action):
    def __init__(self):
        Action.__init__(self, _("Scale..."))

    def has_result(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert iobj
        size = self._make_size(iobj.object)
        fpath = leaf.object
        dirname = os_path.dirname(fpath)
        head, ext = os_path.splitext(os_path.basename(fpath))
        filename = f"{head}_{size}{ext}"
        dpath = utils.get_destpath_in_directory(dirname, filename)
        argv = ["convert", "-scale", str(size), fpath, dpath]
        runtimehelper.register_async_file_result(ctx, dpath)
        _spawn_operation_err(argv)
        return FileLeaf(dpath)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return leaf.is_content_type("image/*")

    def requires_object(self):
        return True

    def object_types(self):
        yield TextLeaf

    @classmethod
    def _make_size(cls, text):
        size = None
        # Allow leading =
        text = text.strip("= ")
        try:
            size = str(float(text.strip()))
        except ValueError:
            with suppress(ValueError):
                twoparts = text.split("x", 1)
                xval = float(twoparts[0].strip())
                yval = float(twoparts[1].strip())
                size = f"{xval:g}x{yval:g}"

        return size

    def valid_object(self, obj, for_item=None):
        return self._make_size(obj.object)

    def get_description(self):
        return _("Scale image to fit inside given pixel measure(s)")


class RotateBase(Action):
    def __init__(self, name, rotation):
        Action.__init__(self, name)
        self.rotation = rotation

    def has_result(self):
        return True

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx

        fpath = leaf.object
        dirname = os_path.dirname(fpath)
        head, ext = os_path.splitext(os_path.basename(fpath))
        filename = f"{head}_{self.rotation}{ext}"
        dpath = utils.get_destpath_in_directory(dirname, filename)
        argv = [
            "jpegtran",
            "-copy",
            "all",
            "-rotate",
            self.rotation,
            "-outfile",
            dpath,
            fpath,
        ]
        runtimehelper.register_async_file_result(ctx, dpath)
        _spawn_operation_err(argv)
        return FileLeaf(dpath)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        return leaf.is_content_type("image/*")


class Rotate90(RotateBase):
    def __init__(self):
        RotateBase.__init__(self, _("Rotate Clockwise"), "90")

    def get_icon_name(self):
        return "object-rotate-right"


class Rotate270(RotateBase):
    def __init__(self):
        RotateBase.__init__(self, _("Rotate Counter-Clockwise"), "270")

    def get_icon_name(self):
        return "object-rotate-left"


class Autorotate(Action):
    def __init__(self):
        Action.__init__(self, _("Autorotate"))

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        fpath = leaf.object
        argv = ["jhead", "-autorot", fpath]
        utils.spawn_async(argv)

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, leaf):
        _root, ext = os_path.splitext(leaf.object)
        if ext.lower() not in (".jpeg", ".jpg"):
            return False
        # Launch jhead to see if 1) it is installed, 2) Orientation nondefault
        try:
            cmdargs = ("jhead", leaf.object)
            with subprocess.Popen(cmdargs, stdout=subprocess.PIPE) as proc:
                out, _err = proc.communicate()
                pretty.print_debug(__name__, "Running", cmdargs)
                return any(
                    li.decode("UTF-8").startswith("Orientation")
                    for li in out.splitlines()
                )

        except OSError:
            pretty.print_debug(__name__, f"Action {self} needs 'jhead'")

        return False

    def get_description(self):
        return _("Rotate JPEG (in-place) according to its EXIF metadata")
