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
    def __init__(self):
        settings = gtk.settings_get_default()
        settings.connect("notify::gtk-color-scheme", self._theme_change)

    @classmethod
    def _theme_change(cls, *ignored):
        cls.glyph_pixbuf_cache.clear()

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
    "folder-saved-search": "/",
    "folder": "/",
    "exec": "$",
    "text-x-script": "$",
    "audio-x-generic": "s",
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
    "edit-select-all": "\"",
    "forward": ">",
    "go-jump": ">",
    "format-text-bold": "A",
    "help-contents": "?",
    "list-add": "+",
    "list-remove": "--",
    "preferences-desktop-locale": "L",
    "help-about": "?",
    "dialog-information": "?",
    "application-exit": "X",
    "window-close": "X",
    "gnome-window-manager": "]",
    "system-shutdown": "X",
    "system-lock-screen": "#",
    "system-log-out": "[",
    "preferences-desktop": "&",
    "user-trash-full": "X",
    "user-home": "~",
    "emblem-favorite": "*",
    #"document-open-recent": u"\N{WATCH}",
    "key_bindings": "3",
    "mail-message-new": "@",
    "edit-copy": "C",
    "edit-paste": "P",
    "edit-clear": "x",
    "edit-undo": "<",
    "view-refresh": "r",
    "drive-removable-media": "=",
    "media-skip-backward": "<",
    "media-skip-forward": ">",
    "media-playback-pause": '"',
    "media-playback-start": ">",
    "package-x-generic": "=",
    "user-info": "p",
    "stock_person": "p",
    ## Applications
    "rhythmbox": "R",
    "terminal": "$",
    "banshee": "B",
    "audacious": "a",
    "totem": "t",
    "vlc": "V",
    "stellarium": "*",
    "preferences-desktop-keyboard": "&",
    "preferences-desktop-keyboard-shortcuts": "&",
    "session-properties": "&",
    "utilities-system-monitor": "#",
    "synaptic": "#",
    "gnome-power-manager": "=",
    "xine": "x",
    "docky": "d",
    "empathy": "@",
    "pidgin": "@",
    "skype": "@",
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
    "openofficeorg3-draw": "D",
    "openofficeorg3-impress": "M",
    "openofficeorg3-calc": "$",
    "libreoffice-writer": "W",
    "libreoffice-draw": "D",
    "libreoffice-impress": "M",
    "libreoffice-calc": "$",
    "abiword_48": "W",
    "abiword": "W",
    "gnumeric": "$",
    "geany": "g",
    "vim": "v",
    "zim": "Z",
    "gimp": "G",
    "inkscape": "N",
    "accessories-dictionary": "A",
    "accessories-character-map": "z",
    "preferences-desktop-theme": "&",
    "help-browser": "?",
    "preferences-desktop-accessibility": "&",
    "gconf-editor": "&",
    # "ALEMBIC"
    "gwibber": "@",
}

unicode_icon_map = {
    "kupfer": "\N{FEMALE SIGN}",
    "gtk-execute": "\N{GEAR}",
    "folder-saved-search": "/",
    "exec": "\N{HAMMER AND PICK}",
    "text-x-script": "\N{HAMMER AND PICK}",
    "audio-x-generic": "s",
    "text-x-generic": "a",
    "text-html": "@",
    "image-x-generic": "c",
    "video-x-generic": "v",
    "application-x-executable": "\N{HAMMER AND PICK}",
    "application-x-generic": "f",

    "applications-office": "\N{HAMMER AND PICK}",
    "applications-science": "\N{STAFF OF AESCULAPIUS}",
    "edit-select-all": "\N{HEAVY DOUBLE TURNED COMMA QUOTATION MARK ORNAMENT}",
    "forward": "\N{RIGHTWARDS ARROW}",
    "go-jump": "\N{CLOCKWISE TOP SEMICIRCLE ARROW}",
    "format-text-bold": "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL A}",
    "help-contents": "\N{DOUBLE QUESTION MARK}",
    "list-add": "+",
    "list-remove": "\N{MINUS SIGN}",
    "preferences-desktop-locale": "\N{WHITE FLAG}",
    "test" : "\N{RADIOACTIVE SIGN}",
    "audio-x-generic": "\N{EIGHTH NOTE}",
    "help-about": "\N{INFORMATION SOURCE}",
    "dialog-information": "\N{INFORMATION SOURCE}",
    "dialog-error": "\N{WARNING SIGN}",
    "application-exit": "\N{SKULL AND CROSSBONES}",
    "window-close": "\N{SKULL AND CROSSBONES}",
    "system-shutdown": "\N{SKULL AND CROSSBONES}",
    "system-log-out": "\N{LEFTWARDS ARROW}",
    "system-lock-screen": "\N{CHIRON}",
    #"system-log-out": u"\N{APL FUNCTIONAL SYMBOL QUAD LEFTWARDS ARROW}",
    "preferences-desktop": "\N{BALLOT BOX WITH CHECK}",
    "user-trash-full": "\N{BLACK UNIVERSAL RECYCLING SYMBOL}",
    "user-trash": "\N{UNIVERSAL RECYCLING SYMBOL}",
    "user-home": "\N{TILDE OPERATOR}",
    #"emblem-favorite": u"\N{BLACK STAR}",
    "emblem-favorite": "\N{HEAVY BLACK HEART}",
    "kupfer-object-multiple": "\N{DOTTED SQUARE}",
    "kupfer-object": "\N{DOTTED SQUARE}",
    "document-open-recent": "\N{WATCH}",
    "key_bindings": "\N{KEYBOARD}",
    "mail-message-new": "\N{ENVELOPE}",
    "edit-copy": "\N{BLACK SCISSORS}",
    "edit-undo": "\N{UNDO SYMBOL}",
    "view-refresh": "\N{CLOCKWISE OPEN CIRCLE ARROW}",
    "folder": "\N{STRICTLY EQUIVALENT TO}",
    "drive-removable-media": "\N{TAPE DRIVE}",
    "media-optical": "\N{TAPE DRIVE}",
    # ok these are stretching it..
    "media-skip-backward": "\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}",
    "media-skip-forward": "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}",
    "media-playback-pause": "\N{MIDDLE DOT}",
    "media-playback-start": "\N{TRIANGULAR BULLET}",
    "package-x-generic": "\N{WHITE DRAUGHTS KING}",
    ## Applications
    "user-info": "\N{BLACK CHESS PAWN}",
    "stock_person": "\N{BLACK CHESS PAWN}",
    "rhythmbox": "\N{BEAMED EIGHTH NOTES}",
    "banshee": "\N{BEAMED EIGHTH NOTES}",
    "audacious": "\N{BEAMED EIGHTH NOTES}",
    "totem": "\N{BEAMED EIGHTH NOTES}",
    "vlc": "\N{BEAMED EIGHTH NOTES}",
    "stellarium": "\N{ASTERISM}",
    "preferences-desktop-keyboard": "\N{KEYBOARD}",
    "preferences-desktop-keyboard-shortcuts": "\N{KEYBOARD}",
    "utilities-system-monitor": "\N{ATOM SYMBOL}",
    "gnome-power-manager": "\N{HIGH VOLTAGE SIGN}",
    "freeciv-client": "\N{CROSSED SWORDS}",
    "xboard": "\N{BLACK CHESS ROOK}",
    "application-games": "\N{BLACK CHESS ROOK}",
    "empathy": "\N{WHITE SMILING FACE}",
    "pidgin": "\N{WHITE SMILING FACE}",
    "skype": "\N{BLACK TELEPHONE}",
    "Thunar": "\N{MALE SIGN}",
    "claws-mail": "\N{ENVELOPE}",
    "icedove": "\N{ENVELOPE}",
    "accessories-text-editor": "\N{WRITING HAND}",
    "openofficeorg3-writer": "\N{WRITING HAND}",
    "libreoffice-writer": "\N{WRITING HAND}",
    "geany": "\N{WRITING HAND}",
    "zim": "\N{WRITING HAND}",
    "gimp": "\N{PENCIL}",
    "openofficeorg3-draw": "\N{PENCIL}",
    "libreoffice-draw": "\N{PENCIL}",
    "openofficeorg3-calc": "\N{GREEK CAPITAL LETTER SIGMA}",
    "libreoffice-calc": "\N{GREEK CAPITAL LETTER SIGMA}",
    "accessories-calculator": "\N{GREEK CAPITAL LETTER SIGMA}",
    "abiword_48": "\N{WRITING HAND}",
    "abiword": "\N{WRITING HAND}",
    "accessories-dictionary": "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL A}",
    "accessories-character-map": "á",
    "preferences-desktop-theme": "\N{EIGHT PETALLED OUTLINED BLACK FLORETTE}",
    "help-browser": "?",
    "preferences-desktop-accessibility": "\N{WHEELCHAIR SYMBOL}",
    #"ALEMBIC"
    "vim": "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL V}",
    "gvim": "\N{MATHEMATICAL DOUBLE-STRUCK CAPITAL V}",
    "gnome-volume-control": "\N{EIGHTH NOTE}",
    "gnumeric": "\N{GREEK CAPITAL LETTER SIGMA}",
    #"gwibber": u"\N{FACSIMILE SIGN}",
    "gwibber": "\N{ENVELOPE}",

    ### marker
    "default": "O",
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
