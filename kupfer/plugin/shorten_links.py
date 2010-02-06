# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Shorten Links")
__kupfer_actions__ = ("ShortenLinks", )
__description__ = _("Create short aliases of long URLs")
__version__ = "2009-12-24"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import re
import httplib
import urllib

from kupfer.objects import Leaf, Action, Source, UrlLeaf
from kupfer import pretty, plugin_support

__kupfer_plugin_category__ = plugin_support.CATEGORY_WEB

_HEADER = {
		'Content-type':'application/x-www-form-urlencoded',
		'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html',
		'Accept-charset': 'utf-8;q=0.7'
}


class _ShortLinksService(Leaf):
	def __init__(self, name):
		Leaf.__init__(self, name, name)
	def get_icon_name(self):
		return "text-html"

class _GETService(_ShortLinksService, pretty.OutputMixin):
	""" A unified shortener service working with GET requests """
	host = None
	path = None
	result_regex = None

	def process(self, url):
		query_string = urllib.urlencode({"url": url})
		try:
			conn = httplib.HTTPConnection(self.host)
			conn.request("GET", self.path+query_string)
			resp = conn.getresponse()
			if resp.status != 200:
				raise ValueError('invalid response %d, %s' % (resp.status,
					resp.reason))
			
			result = resp.read()
			if self.result_regex is not None:
				resurl = re.findall(self.result_regex, result)
				if resurl:
					return resurl[0]
			else:
				return result

		except (httplib.HTTPException, ValueError), err:
			self.output_error(type(err), err)
		return _('Error')


class TinyUrl(_GETService):
	host = "tinyurl.com"
	path = "/api-create.php?"

	def __init__(self):
		_ShortLinksService.__init__(self, u'TinyUrl.com')

class Shorl(_GETService):
	host = 'shorl.com'
	path = '/create.php?'
	result_regex = r'Shorl: \<a href=".+?" rel="nofollow">(.+?)</a>'

	def __init__(self):
		_ShortLinksService.__init__(self, u'Shorl.com')

class BitLy(_GETService):
	host = 'bit.ly'
	path = '/?'
	result_regex = r'\<input id="shortened-url" value="(.+?)" \/\>'

	def __init__(self):
		_ShortLinksService.__init__(self, u'Bit.ly')

UR1CA_HOST='ur1.ca'
UR1CA_PATH=''
UR1CA_RESULT_RE = re.compile(r'\<p class="success">.+?<a href=".+?">(.+?)</a></p>')

class Ur1Ca(_ShortLinksService):
	""" Shorten urls with Ur1.ca """
	def __init__(self):
		_ShortLinksService.__init__(self, u'Ur1.ca')

	def process(self, url):
		if not (url.startswith('http://') or url.startswith('https://') or 
				url.startswith('mailto:')):
			url = 'http://' + url
		query_param = urllib.urlencode(dict(longurl=url, submit='Make it an ur1!'))
		try:
			conn = httplib.HTTPConnection(UR1CA_HOST)
			#conn.debuglevel=255
			conn.request("POST", UR1CA_PATH, query_param, _HEADER)
			resp = conn.getresponse()
			if resp.status != 200:
				raise ValueError('invalid response %d, %s' % (resp.status,
					resp.reason))
			
			result = resp.read()
			resurl = UR1CA_RESULT_RE.findall(result)
			if resurl:
				return resurl[0]
			return _('Error')

		except (httplib.HTTPException, ValueError), err:
			pretty.print_error(__name__, 'TinyUrl.process error', type(err), err)
		return _('Error')


class ShortenLinks(Action):
	''' Shorten links with selected engine '''

	def __init__(self):
		Action.__init__(self, _('Shorten With...'))

	def has_result(self):
		return True

	def activate(self, leaf, iobj):
		result = iobj.process(leaf.object)
		return UrlLeaf(result, result)

	def item_types(self):
		yield UrlLeaf

	def requires_object(self):
		return True

	def object_types(self):
		yield _ShortLinksService

	def object_source(self, for_item=None):
		return ServicesSource()

	def get_description(self):
		return __description__


class ServicesSource(Source):
	def __init__(self):
		Source.__init__(self, _("Services"))

	def get_items(self):
		yield TinyUrl()
		yield Shorl()
		yield Ur1Ca()
		yield BitLy()

	def should_sort_lexically(self):
		return True

	def get_icon_name(self):
		return "applications-internet"
