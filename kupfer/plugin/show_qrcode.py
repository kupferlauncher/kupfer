"""Create QRCodes from texts or urls. Useful for smartphones with QRCode
readers: Create some url with kupfer and QRCode it. Get it with the phone and
use it's browser to display"""

__kupfer_name__ = _("Show QRCode")
__kupfer_actions__ = ("ShowQRCode",)
__description__ = _("Display text as QRCode in a window")
__version__ = "2.0.0"
__author__ = "Thomas Renard <cybaer42@web.de>, KB"

import io

from contextlib import closing

import qrcode
from gi.repository import Gtk, GdkPixbuf

from kupfer.obj import Action, Leaf
from kupfer.ui import uiutils


class ShowQRCode(Action):
    """Create QRCode windows from text or url"""

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
            image = self._create_image(text)
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

    def _create_image(self, text):
        qrc = qrcode.QRCode(box_size=10)
        qrc.add_data(text)
        qrc.make(fit=True)

        # scale barcode if necessary by change box_size
        if qrc.modules_count * 10 > 800:
            qrc.box_size = max(1, 800 // qrc.modules_count)

        return qrc.make_image(fit=True).get_image()
