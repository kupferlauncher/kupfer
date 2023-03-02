from __future__ import annotations

import locale
import typing as ty
from unicodedata import category, normalize


def _folditems():
    _folding_table = {
        # general non-decomposing characters
        # FIXME: This is not complete
        "ł": "l",
        "œ": "oe",
        "ð": "d",
        "þ": "th",
        # germano-scandinavic canonical transliterations
        "ü": "ue",
        "å": "aa",
        "ä": "ae",
        "æ": "ae",
        "ö": "oe",
        "ø": "oe",
    }

    for char, rep in _folding_table.items():
        yield (ord(char.upper()), rep.upper())
        yield (ord(char), rep)

    yield ord("ß"), "ss"
    yield ord("ẞ"), "SS"


_FOLDING_TABLE = dict(_folditems())


def tounicode(utf8str: ty.Union[str, bytes, None]) -> str | None:
    """Return `unicode` from UTF-8 encoded @utf8str
    This is to use the same error handling etc everywhere
    """
    # TODO: check is there other strings than str
    if isinstance(utf8str, str) or utf8str is None:
        return utf8str

    ic_stack(utf8str)
    return utf8str.decode("UTF-8", "replace") if utf8str is not None else ""


# not in use
# def toutf8(ustr: ty.AnyStr) -> bytes:
#     """Return UTF-8 `str` from unicode @ustr
#     This is to use the same error handling etc everywhere
#     if ustr is `str`, just return it
#     """
#     if isinstance(ustr, bytes):
#         return ustr

#     return ustr.encode("UTF-8")


def fromlocale(lstr: bytes) -> str:
    """Return a unicode string from locale bytestring @lstr"""
    assert isinstance(lstr, bytes)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return lstr.decode(enc, "replace")


def tolocale(ustr: str) -> bytes:
    """Return a locale-encoded bytestring from unicode @ustr"""
    assert isinstance(ustr, str)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return ustr.encode(enc)


def tofolded(ustr: str) -> str:
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
    srcstr = normalize("NFKD", ustr.translate(_FOLDING_TABLE))
    return "".join(c for c in srcstr if category(c) != "Mn")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
