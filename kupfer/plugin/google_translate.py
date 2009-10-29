# -*- coding: UTF-8 -*-
from kupfer.objects import Source, Action, TextLeaf, Leaf
from kupfer import utils, pretty

__kupfer_name__ = _("Google Translate")
__kupfer_actions__ = ("Translate", )
__description__ = _("Use Google to Translate Text.")
__version__ = ""
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Translate TextLeaf by Google Translate.

Some parts from pygtranslator: http://xrado.hopto.org
(Radovan Lozej <radovan.lozej@gmail.com).

'''

import httplib
import urllib
from urlparse import urlparse

_GOOGLE_TRANSLATE_URL = 'http://translate.google.com/translate_a/t'
_GOOGLE_TRANS_LANG_URL = 'http://translate.google.com/translate_t'
_HEADERS = {
		'Host':'translate.google.com',
		'User-Agent':'Mozilla/5.0',
		'Accept':'text/xml,application/xml,application/xhtml+xml,text/html',
		'Referer':'http://translate.google.com/translate_t',
		'Content-Type':'application/x-www-form-urlencoded'}


def _translate(text, lang):
	''' Translate @text to @lang. '''
	params = {'sl': 'auto', 'tl': lang, 'text': text, 'client': 't'}
	url = urlparse(_GOOGLE_TRANSLATE_URL)
	try:
		conn = httplib.HTTPConnection(url[1])
		conn.request("POST", url[2], urllib.urlencode(params), _HEADERS)
		resp = conn.getresponse()
	except Exception, err:
		pretty.print_error(__name__, '_translate error', repr(text), lang, err)
		return _("Error connecting to Google Translate")

	header = resp.getheader("Content-Type")
	charset = header[header.index("charset=")+8:]
	if resp.status == 200:
		data = resp.read().decode(charset)
		if data[0] == "[":
			data = data.strip('[]').split(',')
			result = data[0].strip('"')
		else: 
			result = data.strip('"')
	else:
		pretty.print_error(__name__, '_translate status error', repr(text), 
				lang, resp.status, resp.reason)
		result = _("Error")
	conn.close()
	return result


def _load_languages():
	''' Load available languages from Google.
		Generator: (lang_code, lang name) 
	'''
	pretty.print_debug(__name__, '_load_languages')
	url = urlparse(_GOOGLE_TRANS_LANG_URL)
	data = {}
	try:
		conn = httplib.HTTPConnection(url[1])
		conn.request("GET", url[2])
		resp = conn.getresponse()
	except Exception, err:
		pretty.print_error(__name__, '_load_languages error', repr(text), lang,
				err)
	else:
		if resp.status == 200:
			result = resp.read()
			result = result[result.index('select name=tl'):]
			result = result[result.index("<option"):result.index("</select>")]
			rows = result.split("</option>")
			for row in rows:
				if row:
					yield (row[row.index('"')+1:row.rindex('"')], 
						row[row.index('>')+1:])
			conn.close()
			return
		else:
			pretty.print_error(__name__, '_load_languages status error', 
					repr(text), lang, resp.status, resp.reason)
		conn.close()

	yield 'en', 'English'


class Translate (Action):
	def __init__(self):
		Action.__init__(self, _("Translate"))

	def activate(self, leaf, iobj):
		text = unicode(leaf.object)
		dest_lang = iobj.object
		return _TransateQuerySource(text, dest_lang)

	def is_factory(self):
		return True

	def item_types(self):
		yield TextLeaf
	
	def valid_for_item(self, leaf):
		return len(leaf.object.strip()) > 0
	
	def get_description(self):
		return _("Translate in Google")

	def get_icon_name(self):
		return "accessories-dictionary"

	def requires_object(self):
		return True

	def object_types(self):
		yield _Language
	
	def object_source(self, for_item=None):
		return _LangSource()


class _TransateQuerySource(Source):
	def __init__(self, text, lang):
		Source.__init__(self, name=_("Translate into %s") % text)
		self._text = text
		self._lang = lang

	def is_dynamic(self):
		return True
	
	def get_items(self):
		yield TextLeaf(_translate(self._text, self._lang))


class _Language(Leaf):
	pass


class _LangSource(Source):
	_LANG_CACHE = None

	def __init__(self):
		Source.__init__(self, _("Languages"))

	def get_items(self):
		if not self._LANG_CACHE:
			self._LANG_CACHE = tuple((
					_Language(key, _("Translate into %s") % name)
					for key, name in _load_languages()
			))
		return self._LANG_CACHE

	def provides(self):
		yield _Language
