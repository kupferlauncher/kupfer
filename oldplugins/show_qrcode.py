"""Create QRCodes from texts or urls. Useful for smartphones with QRCode
readers: Create some url with kupfer and QRCode it. Get it with the phone and 
use it's browser to display"""

__kupfer_name__ = _("Show QRCode")
__kupfer_actions__ = (
            "ShowQRCode",
    )
__description__ = _("Display text as QRCode in a window")
__version__ = "0.0.2"
__author__ = "Thomas Renard <cybaer42@web.de>"

import io

import gtk
import qrencode

from kupfer.objects import Action, Leaf

class ShowQRCode (Action):
    """Create QRCode windows from text or url"""

    def __init__(self):
        """initialize action"""
        Action.__init__(self, _("Show QRCode"))

    def wants_context(self):
        return True

    def activate(self, leaf, ctx):
        """Create the image from leaf text and display it on window"""

        image_file = io.StringIO()
        text = leaf.get_text_representation()
        version, size, image = qrencode.encode_scaled(text, size=300)
        image.save(image_file, "ppm")
        image_contents = image_file.getvalue()
        image_file.close()

        loader = gtk.gdk.PixbufLoader("pnm")
        loader.write(image_contents, len(image_contents))
        pixbuf = loader.get_pixbuf()
        loader.close()
        window = gtk.Window()
        window.set_default_size(350, 350)
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        window.add(image)
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

