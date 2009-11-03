# -*- coding: UTF-8 -*-

from kupfer.objects import Source, Action, TextLeaf, Leaf, UrlLeaf
from kupfer import icons, utils, pretty

__kupfer_name__ = _("Google Translate")
__kupfer_actions__ = ("Translate", "TranslateUrl", 'OpenTranslatePage')
__description__ = _("Use Google to Translate Text.")
__version__ = "2009-10-31"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Translate TextLeaf by Google Translate.

'''
import httplib
import locale
import urllib
import re

try:
	import cjson
	json_decoder = cjson.decode
except ImportError:
	import json
	json_decoder = json.loads

_GOOGLE_TRANSLATE_HOST = 'translate.google.com'
_GOOGLE_TRANSLATE_PATH = '/translate_a/t?client=t&sl=auto&ie=UTF-8'
_GOOGLE_TRANS_LANG_PATH = '/translate_t'

_HEADER = {
		'Content-type':'application/x-www-form-urlencoded',
		'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html',
		'Accept-charset': 'utf-8;q=0.7'
}

def _parse_encoding_header(response, default="UTF-8"):
	"""Parse response's header for an encoding, that is return 'utf-8' for:
	text/html; charset=utf-8
	"""
	ctype = response.getheader("content-type", "")
	parts = ctype.split("charset=", 1)
	if len(parts) > 1:
		return parts[-1]
	return default


def _translate(text, lang):
	''' Translate @text to @lang. '''
	query_param = urllib.urlencode(dict(tl=lang, text=text.encode('utf-8')))
	try:
		conn = httplib.HTTPConnection(_GOOGLE_TRANSLATE_HOST)
		conn.request("POST", _GOOGLE_TRANSLATE_PATH, query_param, _HEADER)
		resp = conn.getresponse()
		if resp.status != 200:
			raise ValueError('invalid response %d, %s' % resp.status,
					resp.reason)

		response_data = resp.read()
		encoding = _parse_encoding_header(resp)
		response_data = response_data.decode(encoding, 'replace')
		resp = json_decoder(response_data)
		if len(resp) ==  2:
			yield resp[0], ""
		elif len(resp) == 3:
			result, _lang, other_trans = resp
			yield result, ""

			for other in other_trans:
				for translation in other[1:]:
					yield translation, other[0]

	except (httplib.HTTPException, ValueError), err:
		pretty.print_error(__name__, '_translate error', repr(text), lang, err)
		yield  _("Error connecting to Google Translate"), ""

	finally:
		conn.close()


_RE_GET_LANG = re.compile(r'\<option[ \w]+value="(\w+)"\>(\w+)\</option\>', 
		re.UNICODE|re.IGNORECASE)

def _load_languages():
	''' Load available languages from Google.
		Generator: (lang_code, lang name) 
	'''
	user_language = locale.getlocale(locale.LC_MESSAGES)[0]
	pretty.print_debug(__name__, '_load_languages')
	try:
		conn = httplib.HTTPConnection(_GOOGLE_TRANSLATE_HOST)
		headers = {
			"Accept-Language": "%s, en;q=0.7" % user_language,
		}
		conn.request("GET", _GOOGLE_TRANS_LANG_PATH, headers=headers)
		resp = conn.getresponse()
		if resp.status != 200:
			raise ValueError('invalid response %d, %s' % resp.status,
					resp.reason)
		
		result = resp.read().decode(_parse_encoding_header(resp), "replace")
		result = result[result.index('select name=tl'):]
		result = result[:result.index("</select>")]
		for key, name in _RE_GET_LANG.findall(result):
			yield key, name

	except (httplib.HTTPException, ValueError), err:
		pretty.print_error(__name__, '_load_languages error', type(err), err)
		yield 'en', 'English'

	finally:
		conn.close()


class Translate (Action):
	def __init__(self):
		Action.__init__(self, _("Translate To..."))

	def activate(self, leaf, iobj):
		text = unicode(leaf.object)
		dest_lang = iobj.object
		return _TranslateQuerySource(text, dest_lang, unicode(iobj))

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


class TranslationLeaf(TextLeaf):
	def __init__(self, translation, descr):
		TextLeaf.__init__(self, translation)
		self._descrtiption = descr

	def get_description(self):
		return self._descrtiption or TextLeaf.get_description(self)


class _TranslateQuerySource(Source):
	def __init__(self, text, lang, language_name):
		Source.__init__(self, name=_("Translate into %s") % language_name)
		self._text = text
		self._lang = lang

	def get_items(self):
		for translation, desc in _translate(self._text, self._lang):
			yield TranslationLeaf(translation.replace('\\n ', '\n'), desc)


class _Language(Leaf):
	def get_gicon(self):
		return icons.ComposedIcon("text-x-generic","preferences-desktop-locale")


# cache for Languages (load it once)
_LANG_CACHE = None

class _LangSource(Source):

	def __init__(self):
		Source.__init__(self, _("Languages"))

	def get_items(self):
		global _LANG_CACHE
		if not _LANG_CACHE:
			_LANG_CACHE = tuple((
					_Language(key, name.title())
					for key, name in _load_languages()
			))
		return _LANG_CACHE

	def provides(self):
		yield _Language

	def get_icon_name(self):
		return "preferences-desktop-locale"


class TranslateUrl(Action):
	def __init__(self):
		Action.__init__(self, _("Open Page Translated To..."))

	def activate(self, leaf, iobj):
		dest_lang = iobj.object
		params = urllib.urlencode(dict(u=leaf.object, sl='auto', tl=dest_lang ))
		url = 'http://translate.google.pl/translate?' + params
		utils.show_url(url)

	def item_types(self):
		yield UrlLeaf
	
	def valid_for_item(self, leaf):
		return leaf.object.startswith('http://') or leaf.object.startswith('www.')
	
	def get_description(self):
		return _("Translate Page in Google and show in default viewer")

	def get_icon_name(self):
		return "accessories-dictionary"

	def requires_object(self):
		return True

	def object_types(self):
		yield _Language
	
	def object_source(self, for_item=None):
		return _LangSource()


class OpenTranslatePage (Action):
	def __init__(self):
		Action.__init__(self, _("Open Google and Show Translation To..."))

	def activate(self, leaf, iobj):
		text = urllib.quote(unicode(leaf.object).encode('utf-8'))
		dest_lang = iobj.object
		url = 'http://' + _GOOGLE_TRANSLATE_HOST + _GOOGLE_TRANS_LANG_PATH + \
				"#auto|" + dest_lang + "|" + text
		utils.show_url(url)

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


