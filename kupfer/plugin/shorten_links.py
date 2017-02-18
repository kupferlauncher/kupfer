# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Shorten Links")
__kupfer_actions__ = ("ShortenLinks", )
__description__ = _("Create short aliases of long URLs")
__version__ = "2017.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>, US"

import urllib.request, urllib.parse

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
    use_https = False

    def process(self, url):
        """Shorten @url or raise ValueError"""
        query_string = urllib.parse.urlencode({self.url_key : url})
        try:
            pretty.print_debug(__name__, "Request", self.path + query_string)
            resp = urllib.request.urlopen(self.path + query_string)
            if resp.status != 200:
                raise ValueError('Invalid response %d, %s' % (resp.status, resp.reason))
            
            result = resp.read()
            return result.strip().decode("utf-8")

        except (OSError, IOError, ValueError) as exc:
            raise ValueError(exc)
        return _('Error')


# NOTE: It's important that we use only sites that provide a stable API

class IsGd(_GETService):
    """
    Website: http://is.gd
    Reference: http://is.gd/apishorteningreference.php
    """
    path = 'https://is.gd/create.php?format=simple&'

    def __init__(self):
        _ShortLinksService.__init__(self, 'Is.gd')

class VGd(_GETService):
    """
    Website: http://v.gd
    Reference: http://v.gd/apishorteningreference.php

    Like is.gd, but v.gd always shows a preview page.
    """
    path = 'https://v.gd/create.php?format=simple&'

    def __init__(self):
        _ShortLinksService.__init__(self, 'V.gd')


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
            raise OperationError(str(exc))
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
    source_use_cache = False
    def __init__(self):
        super().__init__(_("Services"))

    def get_items(self):
        yield IsGd()
        yield VGd()

    def should_sort_lexically(self):
        return True

    def get_icon_name(self):
        return "applications-internet"
