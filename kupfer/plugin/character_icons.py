# encoding: utf-8
__kupfer_name__ = _("Character Icons")
__kupfer_sources__ = ()
__description__ = _("hi")
__version__ = ""
__author__ = "Ulrik Sverdrup"

import io

import cairo
import gtk

from kupfer import plugin_support

def initialize_plugin(name):
	print "Initialize", name
	plugin_support.register_alternative(__name__, 'icon_renderer', 'ascii',
			name=_("Ascii"), renderer=AsciiIconRenderer())

class AsciiIconRenderer (object):
	glyph_pixbuf_cache = {}
	@classmethod
	def pixbuf_for_name(cls, icon_name, size):
		"""Return pixbuf at @size or None"""
		icon_glyph = ascii_icon_map.get(icon_name)
		if not icon_glyph:
			return None

		pixbuf = cls.glyph_pixbuf_cache.get((icon_glyph, size))
		if not pixbuf:
			pixbuf = get_glyph_pixbuf(icon_glyph, size, False)
			cls.glyph_pixbuf_cache[(icon_glyph, size)] = pixbuf
		return pixbuf

	@classmethod
	def pixbuf_for_file(cls, file_path, icon_size):
		return None

ascii_icon_map = {
	"kupfer": "k",
	"kupfer-object-multiple": "O",
	"kupfer-object": "O",
	"gtk-execute": "x",
	"folder-saved-search": u"/",
	"folder": "/",
	"exec": "$",
	"application-x-generic": "$",
	"applications-office": u"$",
	"edit-select-all": u"\"",
	"forward": u">",
	"go-jump": u">",
	"format-text-bold": u"A",
	"help-contents": u"?",
	"list-add": u"+",
	"list-remove": u"--",
	"preferences-desktop-locale": u"L",
	"audio-x-generic": u"s",
	"help-about": u"?",
	"dialog-information": u"?",
	"application-exit": u"X",
	"window-close": u"X",
	"system-shutdown": u"X",
	"system-lock-screen": u"#",
	#"system-log-out": u"\N{APL FUNCTIONAL SYMBOL QUAD LEFTWARDS ARROW}",
	"preferences-desktop": u"&",
	"user-trash-full": u"X",
	"user-home": u"~",
	#"emblem-favorite": u"\N{BLACK STAR}",
	"emblem-favorite": "*",
	#"document-open-recent": u"\N{WATCH}",
	"key_bindings": u"#",
	"mail-message-new": u"@",
	"edit-copy": u"C",
	#"edit-undo": u"\N{UNDO SYMBOL}",
	"view-refresh": u"r",
	"text-x-generic": u"a",
	"text-html": u"@",
	#"folder": u"=",
	"drive-removable-media": u"=",
	# ok these are stretching it..
	"media-skip-backward": u"<",
	"media-skip-forward": u">",
	"media-playback-pause": '"',
	"media-playback-start": u">",
	"package-x-generic": u"=",
	## Applications
	"user-info": u"p",
	"stock_person": u"p",
	"rhythmbox": u"R",
	#"banshee": u"\N{BEAMED EIGHTH NOTES}",
	#"audacious": u"\N{BEAMED EIGHTH NOTES}",
	#"totem": u"\N{BEAMED EIGHTH NOTES}",
	"vlc": u"V",
	"stellarium": u"*",
	"preferences-desktop-keyboard": "&",
	"preferences-desktop-keyboard-shortcuts": "&",
	"utilities-system-monitor": "#",
	#"gnome-power-manager": u"\N{HIGH VOLTAGE SIGN}",
	#"freeciv-client": u"\N{CROSSED SWORDS}",
	#"xboard": u"\N{BLACK CHESS ROOK}",
	#"empathy": u"\N{WHITE SMILING FACE}",
	#"pidgin": u"\N{WHITE SMILING FACE}",
	#"skype": u"\N{BLACK TELEPHONE}",
	#"Thunar": u"\N{MALE SIGN}",
	"claws-mail": "@",
	"icedove": "@",
	"accessories-text-editor": "g",
	"openofficeorg3-writer": "W",
	"abiword_48": "W",
	"geany": "g",
	#"geany": u"\N{WRITING HAND}",
	#"zim": u"\N{WRITING HAND}",
	#"gimp": u"\N{PENCIL}",
	"gimp": "G",
	#"openofficeorg3-draw": u"\N{PENCIL}",
	"accessories-dictionary": u"A",
	"accessories-character-map": u"z",
	"preferences-desktop-theme": u"&",
	"help-browser": u"?",
	"preferences-desktop-accessibility": u"&",
	# "ALEMBIC"
	"openofficeorg3-calc": u"$",
	"gnumeric": u"$",
	"gwibber": u"@",
	### marker
	"default": u"O",
}

def get_glyph_pixbuf(text, sz, center_vert=True):
	"""Return pixbuf for @text

	if @center_vert, then center completely vertically
	"""
	margin = sz * 0.1
	ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, sz, sz)
	cc = cairo.Context(ims)

	cc.move_to(margin, sz-margin)
	cc.set_font_size(sz)
	cc.set_source_rgba(0,0,0,1)

	cc.text_path(text)
	x1, y1, x2, y2 =cc.path_extents()
	skew_horiz = ((sz-x2) - (x1))/2.0
	skew_vert = ((sz-y2) - (y1))/2.0
	if not center_vert:
		skew_vert = skew_vert*0.2 - margin*0.5
	cc.new_path()
	cc.move_to(margin+skew_horiz, sz-margin+skew_vert)
	cc.text_path(text)
	cc.fill()

	ims.flush()
	f = io.BytesIO()
	ims.write_to_png(f)

	loader = gtk.gdk.PixbufLoader()
	loader.write(f.getvalue())
	loader.close()

	return loader.get_pixbuf()
