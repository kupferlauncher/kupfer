__kupfer_name__ = _("Google Search")
__kupfer_actions__ = ("Search", )
__description__ = _("Search Google with results shown directly")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

import http.client
import urllib.request, urllib.parse, urllib.error

from kupfer.objects import Action, Source, OperationError
from kupfer.objects import TextLeaf, UrlLeaf
from kupfer.plugin import ssl_support

try:
    import cjson
    json_decoder = cjson.decode
except ImportError:
    import json
    json_decoder = json.loads


# Path uses API Key for Kupfer
SEARCH_HOST =  "ajax.googleapis.com"
SEARCH_PATH = ("/ajax/services/search/web?v=1.0&"
               "key=ABQIAAAAV3_egytv7qJVulO0KzPiVRQg95CfKdfDbUDlTS80sgrv"
               "_Zs39hRNkb5m7HV_qLx_d40GexmdjYGvcg&")

class Search (Action):
    def __init__(self):
        Action.__init__(self, _("Google Search"))

    def is_factory(self):
        return True
    def activate(self, leaf):
        return SearchResults(leaf.object)

    def item_types(self):
        yield TextLeaf

    def get_description(self):
        return __description__


class CustomDescriptionUrl (UrlLeaf):
    def __init__(self, obj, title, desc):
        UrlLeaf.__init__(self, obj, title)
        self.description = desc
    def get_description(self):
        return self.description

def _xml_unescape(ustr):
    """Unescape &amp; to &, &lt; to <,  &gt; to >"""
    # important to replace &amp; last here
    return ustr.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

class SearchResults (Source):
    def __init__(self, query):
        Source.__init__(self, _('Results for "%s"') % query)
        self.query = query

    def repr_key(self):
        return self.query

    def get_items(self):
        try:
            query = urllib.parse.urlencode({'q': self.query})
            if ssl_support.is_supported():
                conn = ssl_support.VerifiedHTTPSConnection(SEARCH_HOST,
                                                           timeout=5)
                self.output_debug("Connected to", SEARCH_HOST, "using SSL")
            else:
                conn = http.client.HTTPConnection(SEARCH_HOST, timeout=5)
            conn.request("GET", SEARCH_PATH + query)
            response = conn.getresponse()
            ctype = response.getheader("content-type", default="")
            parts = ctype.split("charset=", 1)
            encoding = parts[-1] if len(parts) > 1 else "UTF-8"
            search_results = response.read().decode(encoding)
            response.close()
        except (IOError, http.client.HTTPException) as exc:
            raise OperationError(str(exc))
        results = json_decoder(search_results)
        data = results['responseData']
        more_results_url = data['cursor']['moreResultsUrl']
        total_results = data['cursor'].get('estimatedResultCount', 0)
        for h in data['results']:
            uq_url = urllib.parse.unquote(h['url'])
            uq_title = _xml_unescape(h['titleNoFormatting'])
            yield UrlLeaf(uq_url, uq_title)
        yield CustomDescriptionUrl(more_results_url,
                _('Show More Results For "%s"') % self.query,
                _("%s total found") % total_results)

    def provides(self):
        yield UrlLeaf

