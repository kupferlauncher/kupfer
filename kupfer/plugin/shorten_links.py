# -*- coding: UTF-8 -*-

import re
import httplib
import urllib

from kupfer.objects import Leaf, Action, Source, UrlLeaf
from kupfer import pretty

__kupfer_name__ = _("Shorten Links")
__kupfer_actions__ = ("ShortenLinks", )
__description__ = _("Shorten links with various services (for now only TinyUrl)")
__version__ = "2009-12-21"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


_HEADER = {
		'Content-type':'application/x-www-form-urlencoded',
		'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html',
		'Accept-charset': 'utf-8;q=0.7'
}


class _ShortLinksService(Leaf):
	def get_icon_name(self):
		return "text-html"


TINYURL_PATH="/api-create.php?"
TINYURL_HOST="tinyurl.com"

class TinyUrl(_ShortLinksService):
	""" Shorten urls with tinyurl.com """
	def __init__(self):
		_ShortLinksService.__init__(self, 'TinyUrl.com', 'TinyUrl.com')

	def process(self, url):
		query_param = urllib.urlencode(dict(url=url))
		try:
			conn = httplib.HTTPConnection(TINYURL_HOST)
			#conn.debuglevel=255
			conn.request("GET", TINYURL_PATH+query_param)
			resp = conn.getresponse()
			if resp.status != 200:
				raise ValueError('invalid response %d, %s' % (resp.status,
					resp.reason))
			
			result = resp.read()
			return result

		except (httplib.HTTPException, ValueError), err:
			pretty.print_error(__name__, 'TinyUrl.process error', type(err), err)
		return _('Error')


SHORL_HOST='shorl.com'
SHORL_PATH='/create.php?'
SHORL_RESULT_RE = re.compile(r'Shorl: \<a href=".+?" rel="nofollow">(.+?)</a>')

class Shorl(_ShortLinksService):
	""" Shorten urls with shorl.com """
	def __init__(self):
		_ShortLinksService.__init__(self, 'Shorl.com', 'Shorl.com')

	def process(self, url):
		query_param = urllib.urlencode(dict(url=url))
		try:
			conn = httplib.HTTPConnection(SHORL_HOST)
			#conn.debuglevel=255
			conn.request("GET", SHORL_PATH+query_param)
			resp = conn.getresponse()
			if resp.status != 200:
				raise ValueError('invalid response %d, %s' % (resp.status,
					resp.reason))
			
			result = resp.read()
			resurl = SHORL_RESULT_RE.findall(result)
			if resurl:
				return resurl[0]
			return _('Error')

		except (httplib.HTTPException, ValueError), err:
			pretty.print_error(__name__, 'TinyUrl.process error', type(err), err)
		return _('Error')


UR1CA_HOST='ur1.ca'
UR1CA_PATH=''
UR1CA_RESULT_RE = re.compile(r'\<p class="success">.+?<a href=".+?">(.+?)</a></p>')

class Ur1Ca(_ShortLinksService):
	""" Shorten urls with Ur1.ca """
	def __init__(self):
		_ShortLinksService.__init__(self, 'Ur1.ca', 'Ur1.ca')

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
		Action.__init__(self, _('Shorten Link...'))

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


class ServicesSource(Source):
	def __init__(self):
		Source.__init__(self, _("Services"))

	def get_items(self):
		yield TinyUrl()
		yield Shorl()
		yield Ur1Ca()

	def get_icon_name(self):
		return "applications-internet"
