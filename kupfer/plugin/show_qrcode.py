"""Create QRCodes from texts or urls. Useful for smartphones with QRCode
readers: Create some url with kupfer and QRCode it. Get it with the phone and
use it's browser to display"""

__kupfer_name__ = _("Show QRCode")
__kupfer_actions__ = ("ShowQRCode", "CreateQRCode", "CreateTextQRCode")
__description__ = _("Display text as QRCode in a window")
__version__ = "2.0.0"
__author__ = "Thomas Renard <cybaer42@web.de>, KB"

import io
import tempfile
from contextlib import closing
from gettext import gettext as _

import qrcode

from gi.repository import GdkPixbuf, Gtk

from kupfer import plugin_support
from kupfer.obj import Action, FileLeaf, Leaf, TextLeaf
from kupfer.ui import uiutils


if not hasattr(qrcode, "QRCode"):
    raise ImportError("missing (right) qrcode package")


__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "max_size",
        "label": _("Max QRCode size (pixels)"),
        "type": int,
        "value": 800,
    },
)


class ShowQRCode(Action):
    """Create QRCode windows from text or url"""

    rank_adjust = -5

    def __init__(self):
        """initialize action"""
        Action.__init__(self, _("Show QRCode"))

    def wants_context(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        """Create the image from leaf text and display it on window"""

        assert ctx
        try:
            text = leaf.get_text_representation()
            image = _create_image(text)
        except ValueError as err:
            uiutils.show_text_result(
                _("Cannot create QRCode: %s") % err, _("Show QRCode"), ctx
            )
            return

        width, height = image.size

        with io.BytesIO() as image_file:
            image.save(image_file, "ppm")
            image_contents = image_file.getvalue()

            with closing(GdkPixbuf.PixbufLoader.new()) as loader:
                loader.write(image_contents)
                pixbuf = loader.get_pixbuf()

        window = Gtk.Window()
        window.set_default_size(width, height)
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        window.add(image)  # pylint: disable=no-member

        ctx.environment.present_window(window)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return hasattr(leaf, "get_text_representation")

    def get_description(self):
        """The Action description"""
        return _("Display text as QRCode in a window")

    def get_icon_name(self):
        """Name of the icon"""
        return "format-text-bold"


class CreateQRCode(Action):
    rank_adjust = -5

    def __init__(self):
        """initialize action"""
        Action.__init__(self, _("Create QRCode image"))

    def wants_context(self):
        return True

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        try:
            text = leaf.get_text_representation()
            image = _create_image(text)
        except ValueError as err:
            uiutils.show_text_result(
                _("Cannot create QRCode: %s") % err, _("Show QRCode"), ctx
            )
            return None

        with tempfile.NamedTemporaryFile(
            suffix=".png", prefix="qrcode_", delete=False
        ) as file:
            image.save(file, "png")
            return FileLeaf(file.name)

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return hasattr(leaf, "get_text_representation")

    def get_description(self):
        """The Action description"""
        return _("Create PNG file with QRCode")

    def get_icon_name(self):
        """Name of the icon"""
        return "document-new"


class CreateTextQRCode(Action):
    """Create QRCode as unicode text and return it"""

    rank_adjust = -5

    def __init__(self):
        """initialize action"""
        Action.__init__(self, _("Create QRCode text"))

    def wants_context(self):
        return True

    def has_result(self):
        return True

    def activate(self, leaf, iobj=None, ctx=None):
        assert ctx
        try:
            text = leaf.get_text_representation()
            qrc = qrcode.QRCode(box_size=10)
            qrc.add_data(text)
            qrc.make(fit=True)

        except ValueError as err:
            uiutils.show_text_result(
                _("Cannot create QRCode: %s") % err, _("Show QRCode"), ctx
            )
            return None

        with io.StringIO() as buf:
            qrc.print_ascii(out=buf)
            buf.seek(0)
            return TextLeaf(buf.getvalue())

    def item_types(self):
        yield Leaf

    def valid_for_item(self, leaf):
        return hasattr(leaf, "get_text_representation")

    def get_description(self):
        """The Action description"""
        return _("Create QRCode as text with unicode characters")

    def get_icon_name(self):
        """Name of the icon"""
        return "document-new"


def _create_image(text):
    qrc = qrcode.QRCode(box_size=10)
    qrc.add_data(text)
    qrc.make(fit=True)

    # scale barcode if necessary by change box_size
    max_size = int(__kupfer_settings__["max_size"] or 800)
    if max_size < 0:
        max_size = 800

    if qrc.modules_count * 10 > max_size:
        qrc.box_size = max(1, max_size // qrc.modules_count)

    return qrc.make_image(fit=True).get_image()
