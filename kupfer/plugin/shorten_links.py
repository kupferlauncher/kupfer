# -*- coding: UTF-8 -*-

import httplib
import urllib

from kupfer.objects import Leaf, Action, Source, UrlLeaf
from kupfer import pretty

__kupfer_name__ = _("Shorten Links")
__kupfer_actions__ = ("ShortenLinks", )
__description__ = _("Shorten links with various services (for now only TinyUrl)")
__version__ = "2009-12-21"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"


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

	def get_icon_name(self):
		return "applications-internet"
