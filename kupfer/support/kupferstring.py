from __future__ import annotations

import locale
import typing as ty
from functools import cmp_to_key
from unicodedata import category, normalize

from .datatools import evaluate_once


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
    if isinstance(utf8str, str) or utf8str is None:
        return utf8str

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


@evaluate_once
def get_encoding() -> str:
    return locale.getpreferredencoding(do_setlocale=False)


def fromlocale(lstr: bytes) -> str:
    """Return a unicode string from locale bytestring @lstr"""
    assert isinstance(lstr, bytes)
    return lstr.decode(get_encoding(), "replace")


def tolocale(ustr: str) -> bytes:
    """Return a locale-encoded bytestring from unicode @ustr"""
    assert isinstance(ustr, str)
    return ustr.encode(get_encoding())


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


_SortItem = ty.TypeVar("_SortItem")


def locale_sort(
    seq: ty.Iterable[_SortItem], key: ty.Callable[[_SortItem], ty.Any] = str
) -> list[_SortItem]:
    """Return @seq of objects with @key function as a list sorted
    in locale lexical order

    >>> locale.setlocale(locale.LC_ALL, "C")
    'C'
    >>> locale_sort("abcABC")
    ['A', 'B', 'C', 'a', 'b', 'c']

    >>> locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    'en_US.UTF-8'
    >>> locale_sort("abcABC")
    ['a', 'A', 'b', 'B', 'c', 'C']
    """

    def locale_cmp(val1, val2):
        return locale.strcoll(key(val1), key(val2))

    seq = seq if isinstance(seq, list) else list(seq)
    seq.sort(key=cmp_to_key(locale_cmp))
    return seq


if __name__ == "__main__":
    import doctest

    doctest.testmod()
