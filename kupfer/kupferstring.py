# -*- encoding: UTF-8 -*-

import locale
from unicodedata import normalize, category

def _folditems():
    _folding_table = {
        # general non-decomposing characters
        # FIXME: This is not complete
        "ł" : "l",
        "œ" : "oe",
        "ð" : "d",
        "þ" : "th",
        # germano-scandinavic canonical transliterations
        "ü" : "ue",
        "å" : "aa",
        "ä" : "ae",
        "æ" : "ae",
        "ö" : "oe",
        "ø" : "oe",
    }

    for c, rep in list(_folding_table.items()):
        yield (ord(c.upper()), rep.upper())
        yield (ord(c), rep)
    yield ord("ß"), "ss"
    yield ord("ẞ"), "SS"

folding_table = dict(_folditems())

def tounicode(utf8str):
    """Return `unicode` from UTF-8 encoded @utf8str
    This is to use the same error handling etc everywhere
    """
    if isinstance(utf8str, str):
        return utf8str
    return utf8str.decode("UTF-8", "replace") if utf8str is not None else ""

def toutf8(ustr):
    """Return UTF-8 `str` from unicode @ustr
    This is to use the same error handling etc everywhere
    if ustr is `str`, just return it
    """
    if isinstance(ustr, bytes):
        return ustr
    return ustr.encode("UTF-8")

def fromlocale(lstr):
    """Return a unicode string from locale bytestring @lstr"""
    assert isinstance(lstr, bytes)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return lstr.decode(enc, "replace")

def tolocale(ustr):
    """Return a locale-encoded bytestring from unicode @ustr"""
    assert isinstance(ustr, str)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return ustr.encode(enc)


def tofolded(ustr):
    """Fold @ustr

    Return a unicode string where composed characters are replaced by
    their base, and extended latin characters are replaced by
    similar basic latin characters.

    >>> tofolded(u"Wyłącz")
    'Wylacz'
    >>> tofolded(u"naïveté")
    'naivete'
    >>> tofolded(u"Groß")
    'Gross'

    Characters from other scripts are not transliterated.

    >>> print(tofolded(u"Ἑλλάς"))
    Ελλας
    """
    srcstr = normalize("NFKD", ustr.translate(folding_table))
    return "".join([c for c in srcstr if category(c) != 'Mn'])

if __name__ == '__main__':
    import doctest
    doctest.testmod()
