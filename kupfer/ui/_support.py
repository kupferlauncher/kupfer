#! /usr/bin/env python3

"""
UI support functions

"""

from gi.repository import Gtk

from kupfer.support import datatools

_escape_table = {
    ord("&"): "&amp;",
    ord("<"): "&lt;",
    ord(">"): "&gt;",
}


def escape_markup_str(mstr: str) -> str:
    """Use a simple homegrown replace table to replace &, <, > with
    entities in @mstr
    """
    return mstr.translate(_escape_table)


@datatools.evaluate_once
def text_direction_is_ltr() -> bool:
    """Check is system is configured as left-to-right."""
    return Gtk.Widget.get_default_direction() != Gtk.TextDirection.RTL  # type: ignore


def normalize_display_name(name: str) -> str:
    # NOT IN USE
    if name[-2] == ":":
        return name + ".0"

    return name


# # NOT IN USE
# def make_rounded_rect(cr, x, y, width, height, radius):
#     """
#     Draws a rounded rectangle with corners of @radius
#     """
#     MPI = math.pi
#     cr.save()

#     cr.move_to(radius, 0)
#     cr.line_to(width-radius,0)
#     cr.arc(width-radius, radius, radius, 3*MPI/2, 2*MPI)
#     cr.line_to(width, height-radius)
#     cr.arc(width-radius, height-radius, radius, 0, MPI/2)
#     cr.line_to(radius, height)
#     cr.arc(radius, height-radius, radius, MPI/2, MPI)
#     cr.line_to(0, radius)
#     cr.arc(radius, radius, radius, MPI, 3*MPI/2)
#     cr.close_path()
#     cr.restore()


# # not in use
# def get_glyph_pixbuf(
#     text: str,
#     size: int,
#     center_vert: bool = True,
#     color: tuple[int, int, int] | None = None,
# ) -> GdkPixbuf.Pixbuf:
#     """Return pixbuf for @text

#     if @center_vert, then center completely vertically
#     """
#     margin = size * 0.1
#     ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
#     cctx = cairo.Context(ims)

#     cctx.move_to(margin, size - margin)
#     cctx.set_font_size(size / 2)
#     if color is None:
#         cctx.set_source_rgba(0, 0, 0, 1)
#     else:
#         cctx.set_source_rgb(*color)

#     cctx.text_path(text)
#     x1, y1, x2, y2 = cctx.path_extents()
#     skew_horiz = ((size - x2) - x1) / 2.0
#     skew_vert = ((size - y2) - y1) / 2.0
#     if not center_vert:
#         skew_vert = skew_vert * 0.2 - margin * 0.5

#     cctx.new_path()
#     cctx.move_to(margin + skew_horiz, size - margin + skew_vert)
#     cctx.text_path(text)
#     cctx.fill()

#     ims.flush()
#     pngfile = io.BytesIO()
#     ims.write_to_png(pngfile)

#     loader = GdkPixbuf.PixbufLoader()
#     loader.write(pngfile.getvalue())
#     loader.close()

#     return loader.get_pixbuf()
