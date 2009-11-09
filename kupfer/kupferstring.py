# -*- encoding: UTF-8 -*-

import locale
from unicodedata import normalize, category

def _folditems():
	_folding_table = {
		# general non-decomposing characters
		# FIXME: This is not complete
		u"ł" : u"l",
		u"œ" : u"oe",
		u"ð" : u"d",
		u"þ" : u"th",
		u"ß" : u"ss",
		# germano-scandinavic canonical transliterations
		u"ü" : u"ue",
		u"å" : u"aa",
		u"ä" : u"ae",
		u"æ" : u"ae",
		u"ö" : u"oe",
		u"ø" : u"oe",
	}

	for c, rep in _folding_table.iteritems():
		yield (ord(c.upper()), rep.title())
		yield (ord(c), rep)

folding_table = dict(_folditems())

def tounicode(utf8str):
	"""Return `unicode` from UTF-8 encoded @utf8str
	This is to use the same error handling etc everywhere
	"""
	return utf8str.decode("UTF-8", "replace") if utf8str is not None else u""

def toutf8(ustr):
	"""Return UTF-8 `str` from unicode @ustr
	This is to use the same error handling etc everywhere
	if ustr is `str`, just return it
	"""
	if isinstance(ustr, str):
		return ustr
	return ustr.encode("UTF-8", "replace")

def fromlocale(lstr):
	"""Return a unicode string from locale bytestring @lstr"""
	enc = locale.getpreferredencoding(do_setlocale=False)
	return lstr.decode(enc, "replace")


def tofolded(ustr):
	u"""Fold @ustr

	Return a unicode string where composed characters are replaced by
	their base, and extended latin characters are replaced by
	similar basic latin characters.

	>>> tofolded(u"Wyłącz")
	u'Wylacz'
	>>> tofolded(u"naïveté")
	u'naivete'

	Characters from other scripts are not transliterated.

	>>> print tofolded(u"Ἑλλάς")
	Ελλας
	"""
	srcstr = normalize("NFKD", ustr.translate(folding_table))
	return u"".join([c for c in srcstr if category(c) != 'Mn'])

if __name__ == '__main__':
	import sys
	reload(sys)
	sys.setdefaultencoding("UTF-8")

	import doctest
	doctest.testmod()
