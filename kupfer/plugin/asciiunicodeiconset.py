# encoding: utf-8
# don't panic! This is just because it's crazy and fun! ツ
__kupfer_name__ = _("Ascii & Unicode Icon Set")
__kupfer_sources__ = ()
__description__ = _("Provides the Ascii and Unicode icon sets that"
                    " use letters and symbols to produce icons for"
                    " the objects found in Kupfer.")
__version__ = ""
__author__ = "Ulrik Sverdrup"

import io
import weakref

import cairo
import gtk

from kupfer import plugin_support

def initialize_plugin(name):
	plugin_support.register_alternative(__name__, 'icon_renderer', 'ascii',
			name=_("Ascii"), renderer=AsciiIconRenderer())
	plugin_support.register_alternative(__name__, 'icon_renderer', 'unicode',
			name=_("Unicode"), renderer=UnicodeIconRenderer())

def text_color():
	"color as triple or None"
	settings = gtk.settings_get_default()
	s = gtk.rc_get_style_by_paths(settings, "kupfer.*", None, None)
	if not s:
		e = gtk.Invisible()
		e.realize()
		s = e.style
	c = s.fg[gtk.STATE_NORMAL]
	return (1.0*c.red/0xffff, 1.0*c.green/0xffff, 1.0*c.blue/0xffff)

class AsciiIconRenderer (object):
	glyph_pixbuf_cache = weakref.WeakValueDictionary()
	def __init__(self):
		settings = gtk.settings_get_default()
		settings.connect("notify::gtk-color-scheme", self._theme_change)

	@classmethod
	def _theme_change(cls, *ignored):
		cls.glyph_pixbuf_cache.clear()

	@classmethod
	def pixbuf_for_name(cls, icon_name, size):
		"""Return pixbuf at @size or None"""
		icon_glyph = ascii_icon_map.get(icon_name)
		if not icon_glyph:
			return None


		pixbuf = cls.glyph_pixbuf_cache.get((icon_glyph, size))
		if not pixbuf:
			pixbuf = get_glyph_pixbuf(icon_glyph, size, False, text_color())

			cls.glyph_pixbuf_cache[(icon_glyph, size)] = pixbuf
		return pixbuf

	@classmethod
	def pixbuf_for_file(cls, file_path, icon_size):
		return None

class UnicodeIconRenderer (object):
	glyph_pixbuf_cache = weakref.WeakValueDictionary()
	@classmethod
	def pixbuf_for_name(cls, icon_name, size):
		"""Return pixbuf at @size or None"""
		icon_glyph = unicode_icon_map.get(icon_name)
		if not icon_glyph:
			return None

		pixbuf = cls.glyph_pixbuf_cache.get((icon_glyph, size))
		if not pixbuf:
			pixbuf = get_glyph_pixbuf(icon_glyph, size, False, text_color())
			cls.glyph_pixbuf_cache[(icon_glyph, size)] = pixbuf
		return pixbuf

	@classmethod
	def pixbuf_for_file(cls, file_path, icon_size):
		return None

ascii_icon_map = {
	"kupfer": "k",
	"kupfer-object-multiple": "O",
	"kupfer-object": "O",
	"gtk-execute": "o",
	## filetypes
	"folder-saved-search": u"/",
	"folder": "/",
	"exec": "$",
	"text-x-script": "$",
	"audio-x-generic": u"s",
	"text-x-generic": "a",
	"text-html": "@",
	"image-x-generic": "c",
	"video-x-generic": "v",
	"application-x-executable": "$",
	"application-x-generic": "f",
	#"gnome-mime-application-pdf": "f",
	#"x-office-document": "f",
	## actions
	"document-open-recent": "1",
	"applications-office": "$",
	"applications-internet": "S",
	"edit-select-all": u"\"",
	"forward": u">",
	"go-jump": u">",
	"format-text-bold": u"A",
	"help-contents": u"?",
	"list-add": u"+",
	"list-remove": u"--",
	"preferences-desktop-locale": u"L",
	"help-about": u"?",
	"dialog-information": u"?",
	"application-exit": u"X",
	"window-close": u"X",
	"gnome-window-manager": "]",
	"system-shutdown": u"X",
	"system-lock-screen": u"#",
	"system-log-out": u"[",
	"preferences-desktop": u"&",
	"user-trash-full": u"X",
	"user-home": u"~",
	"emblem-favorite": "*",
	#"document-open-recent": u"\N{WATCH}",
	"key_bindings": u"3",
	"mail-message-new": u"@",
	"edit-copy": "C",
	"edit-paste": "P",
	"edit-clear": "x",
	"edit-undo": "<",
	"view-refresh": "r",
	"drive-removable-media": u"=",
	"media-skip-backward": u"<",
	"media-skip-forward": u">",
	"media-playback-pause": '"',
	"media-playback-start": u">",
	"package-x-generic": u"=",
	"user-info": "p",
	"stock_person": "p",
	## Applications
	"rhythmbox": "R",
	"terminal": "$",
	"banshee": "B",
	"audacious": u"a",
	"totem": "t",
	"vlc": u"V",
	"stellarium": u"*",
	"preferences-desktop-keyboard": "&",
	"preferences-desktop-keyboard-shortcuts": "&",
	"session-properties": "&",
	"utilities-system-monitor": "#",
	"synaptic": "#",
	"gnome-power-manager": u"=",
	"xine": u"x",
	"docky": "d",
	"empathy": u"@",
	"pidgin": u"@",
	"skype": u"@",
	"accessories-calculator": "=",
	"dia": "D",
	"mypaint": "y",
	"liferea": "L",
	"freeciv-client": "C",
	"qbittorrent": "q",
	"gnome-display-properties" : "]",
	"preferences-desktop-screensaver": "]",
	#"Thunar": u"\N{MALE SIGN}",
	"claws-mail": "@",
	"icedove": "@",
	"gajim": "@",
	"iceweasel": "@",
	"firefox": "@",
	"tomboy": "T",
	"gnome-specimen" : "Q",
	"accessories-text-editor": "g",
	"openofficeorg3-writer": "W",
	"openofficeorg3-draw": u"D",
	"openofficeorg3-impress": u"M",
	"openofficeorg3-calc": u"$",
	"libreoffice-writer": "W",
	"libreoffice-draw": u"D",
	"libreoffice-impress": u"M",
	"libreoffice-calc": u"$",
	"abiword_48": "W",
	"abiword": "W",
	"gnumeric": u"$",
	"geany": "g",
	"vim": "v",
	"zim": u"Z",
	"gimp": "G",
	"inkscape": "N",
	"accessories-dictionary": u"A",
	"accessories-character-map": u"z",
	"preferences-desktop-theme": u"&",
	"help-browser": u"?",
	"preferences-desktop-accessibility": u"&",
	"gconf-editor": "&",
	# "ALEMBIC"
	"gwibber": u"@",
}

unicode_icon_map = {
	"kupfer": u"\N{FEMALE SIGN}",
	"gtk-execute": u"\N{GEAR}",
	"folder-saved-search": u"/",
	"exec": u"\N{HAMMER AND PICK}",
	"text-x-script": u"\N{HAMMER AND PICK}",
	"audio-x-generic": u"s",
	"text-x-generic": "a",
	"text-html": "@",
	"image-x-generic": "c",
	"video-x-generic": "v",
	"application-x-executable": u"\N{HAMMER AND PICK}",
	"application-x-generic": "f",

	"applications-office": u"\N{HAMMER AND PICK}",
	"applications-science": u"\N{STAFF OF AESCULAPIUS}",
	"edit-select-all": u"\N{HEAVY DOUBLE TURNED COMMA QUOTATION MARK ORNAMENT}",
	"forward": u"\N{RIGHTWARDS ARROW}",
	"go-jump": u"\N{CLOCKWISE TOP SEMICIRCLE ARROW}",
	"format-text-bold": u"\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL A}",
	"help-contents": u"\N{DOUBLE QUESTION MARK}",
	"list-add": u"+",
	"list-remove": u"\N{MINUS SIGN}",
	"preferences-desktop-locale": u"\N{WHITE FLAG}",
	"test" : u"\N{RADIOACTIVE SIGN}",
	"audio-x-generic": u"\N{EIGHTH NOTE}",
	"help-about": u"\N{INFORMATION SOURCE}",
	"dialog-information": u"\N{INFORMATION SOURCE}",
	"dialog-error": u"\N{WARNING SIGN}",
	"application-exit": u"\N{SKULL AND CROSSBONES}",
	"window-close": u"\N{SKULL AND CROSSBONES}",
	"system-shutdown": u"\N{SKULL AND CROSSBONES}",
	"system-log-out": u"\N{LEFTWARDS ARROW}",
	"system-lock-screen": u"\N{CHIRON}",
	#"system-log-out": u"\N{APL FUNCTIONAL SYMBOL QUAD LEFTWARDS ARROW}",
	"preferences-desktop": u"\N{BALLOT BOX WITH CHECK}",
	"user-trash-full": u"\N{BLACK UNIVERSAL RECYCLING SYMBOL}",
	"user-trash": u"\N{UNIVERSAL RECYCLING SYMBOL}",
	"user-home": u"\N{TILDE OPERATOR}",
	#"emblem-favorite": u"\N{BLACK STAR}",
	"emblem-favorite": u"\N{HEAVY BLACK HEART}",
	"kupfer-object-multiple": u"\N{DOTTED SQUARE}",
	"kupfer-object": u"\N{DOTTED SQUARE}",
	"document-open-recent": u"\N{WATCH}",
	"key_bindings": u"\N{KEYBOARD}",
	"mail-message-new": u"\N{ENVELOPE}",
	"edit-copy": u"\N{BLACK SCISSORS}",
	"edit-undo": u"\N{UNDO SYMBOL}",
	"view-refresh": u"\N{CLOCKWISE OPEN CIRCLE ARROW}",
	"folder": u"\N{STRICTLY EQUIVALENT TO}",
	"drive-removable-media": u"\N{TAPE DRIVE}",
	"media-optical": u"\N{TAPE DRIVE}",
	# ok these are stretching it..
	"media-skip-backward": u"\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}",
	"media-skip-forward": u"\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}",
	"media-playback-pause": u"\N{MIDDLE DOT}",
	"media-playback-start": u"\N{TRIANGULAR BULLET}",
	"package-x-generic": u"\N{WHITE DRAUGHTS KING}",
	## Applications
	"user-info": u"\N{BLACK CHESS PAWN}",
	"stock_person": u"\N{BLACK CHESS PAWN}",
	"rhythmbox": u"\N{BEAMED EIGHTH NOTES}",
	"banshee": u"\N{BEAMED EIGHTH NOTES}",
	"audacious": u"\N{BEAMED EIGHTH NOTES}",
	"totem": u"\N{BEAMED EIGHTH NOTES}",
	"vlc": u"\N{BEAMED EIGHTH NOTES}",
	"stellarium": u"\N{ASTERISM}",
	"preferences-desktop-keyboard": u"\N{KEYBOARD}",
	"preferences-desktop-keyboard-shortcuts": u"\N{KEYBOARD}",
	"utilities-system-monitor": u"\N{ATOM SYMBOL}",
	"gnome-power-manager": u"\N{HIGH VOLTAGE SIGN}",
	"freeciv-client": u"\N{CROSSED SWORDS}",
	"xboard": u"\N{BLACK CHESS ROOK}",
	"application-games": u"\N{BLACK CHESS ROOK}",
	"empathy": u"\N{WHITE SMILING FACE}",
	"pidgin": u"\N{WHITE SMILING FACE}",
	"skype": u"\N{BLACK TELEPHONE}",
	"Thunar": u"\N{MALE SIGN}",
	"claws-mail": u"\N{ENVELOPE}",
	"icedove": u"\N{ENVELOPE}",
	"accessories-text-editor": u"\N{WRITING HAND}",
	"openofficeorg3-writer": u"\N{WRITING HAND}",
	"libreoffice-writer": u"\N{WRITING HAND}",
	"geany": u"\N{WRITING HAND}",
	"zim": u"\N{WRITING HAND}",
	"gimp": u"\N{PENCIL}",
	"openofficeorg3-draw": u"\N{PENCIL}",
	"libreoffice-draw": u"\N{PENCIL}",
	"openofficeorg3-calc": u"\N{GREEK CAPITAL LETTER SIGMA}",
	"libreoffice-calc": u"\N{GREEK CAPITAL LETTER SIGMA}",
	"accessories-calculator": u"\N{GREEK CAPITAL LETTER SIGMA}",
	"abiword_48": u"\N{WRITING HAND}",
	"abiword": u"\N{WRITING HAND}",
	"accessories-dictionary": u"\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL A}",
	"accessories-character-map": u"á",
	"preferences-desktop-theme": u"\N{EIGHT PETALLED OUTLINED BLACK FLORETTE}",
	"help-browser": u"?",
	"preferences-desktop-accessibility": u"\N{WHEELCHAIR SYMBOL}",
	#"ALEMBIC"
	"vim": u"\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL V}",
	"gvim": u"\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL V}",
	"gnome-volume-control": u"\N{EIGHTH NOTE}",
	"gnumeric": u"\N{GREEK CAPITAL LETTER SIGMA}",
	#"gwibber": u"\N{FACSIMILE SIGN}",
	"gwibber": u"\N{ENVELOPE}",

	### marker
	"default": u"O",
}

def get_glyph_pixbuf(text, sz, center_vert=True, color=None):
	"""Return pixbuf for @text

	if @center_vert, then center completely vertically
	"""
	margin = sz * 0.1
	ims = cairo.ImageSurface(cairo.FORMAT_ARGB32, sz, sz)
	cc = cairo.Context(ims)

	cc.move_to(margin, sz-margin)
	cc.set_font_size(sz)
	if color is None:
		cc.set_source_rgba(0,0,0,1)
	else:
		cc.set_source_rgb(*color)

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
