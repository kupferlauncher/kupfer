# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Shorten Links")
__kupfer_actions__ = ("ShortenLinks", )
__description__ = _("Create short aliases of long URLs")
__version__ = "2011-03-01"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import httplib
import urllib

from kupfer.objects import Leaf, Action, Source, UrlLeaf, OperationError
from kupfer import pretty

class _ShortLinksService(Leaf):
	def __init__(self, name):
		Leaf.__init__(self, name, name)
	def get_icon_name(self):
		return "text-html"

class _GETService(_ShortLinksService, pretty.OutputMixin):
	""" A unified shortener service working with GET requests """
	host = None
	path = None
	url_key = "url"

	def process(self, url):
		"""Shorten @url or raise ValueError"""
		query_string = urllib.urlencode({self.url_key : url})
		try:
			conn = httplib.HTTPConnection(self.host)
			conn.request("GET", self.path+query_string)
			resp = conn.getresponse()
			if resp.status != 200:
				raise ValueError('Invalid response %d, %s' % (resp.status,
					resp.reason))
			
			result = resp.read()
			return result.strip()

		except (httplib.HTTPException, ValueError) as exc:
			raise ValueError(exc)
		return _('Error')


# NOTE: It's important that we use only sites that provide a stable API

class TinyUrl(_GETService):
	"""
	Website: http://tinyurl.com
	"""
	host = "tinyurl.com"
	path = "/api-create.php?"

	def __init__(self):
		_ShortLinksService.__init__(self, u'TinyUrl.com')

class IsGd(_GETService):
	"""
	Website: http://is.gd
	Reference: http://is.gd/apishorteningreference.php
	"""
	host = 'is.gd'
	path = '/create.php?format=simple&'

	def __init__(self):
		_ShortLinksService.__init__(self, u'Is.gd')

class VGd(_GETService):
	"""
	Website: http://v.gd
	Reference: http://v.gd/apishorteningreference.php

	Like is.gd, but v.gd always shows a preview page.
	"""
	host = 'v.gd'
	path = '/create.php?format=simple&'

	def __init__(self):
		_ShortLinksService.__init__(self, u'V.gd')

class BitLy(_GETService):
	"""
	Website: http://bit.ly
	Reference: http://code.google.com/p/bitly-api/wiki/ApiDocumentation
	"""
	# No password is available for this login name,
	# yet there is a possibility that you could track
	# all URLs shortened using this API key
	BITLY_LOGIN = "kupferkupfer"
	BITLY_API_KEY = "R_a617770f00b647d6c22ce162105125c2"

	host = 'bit.ly'
	path = ('http://api.bitly.com/v3/shorten?login=%s&apiKey=%s&format=txt&' %
			(BITLY_LOGIN, BITLY_API_KEY))
	url_key = "longUrl"

	def __init__(self):
		_ShortLinksService.__init__(self, u'Bit.ly')


class ShortenLinks(Action):
	''' Shorten links with selected engine '''

	def __init__(self):
		Action.__init__(self, _('Shorten With...'))

	def has_result(self):
		return True

	def activate(self, leaf, iobj):
		try:
			result = iobj.process(leaf.object)
		except ValueError as exc:
			raise OperationError(unicode(exc))
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
		yield IsGd()
		yield VGd()
		yield BitLy()

	def should_sort_lexically(self):
		return True

	def get_icon_name(self):
		return "applications-internet"
