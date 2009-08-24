import os
import urllib
import xml.sax

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf
from kupfer import utils, config

from kupfer.plugin import firefox_support, xml_support

__kupfer_name__ = _("Search the Web")
__kupfer_sources__ = ("OpenSearchSource", )
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"GoogleSearch",
		"SearchWithEngine",
	)
__description__ = _("Search the web with OpenSearch search engines")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class OpenSearchHandler (xml_support.XMLEntryHandler):
	def startElement(self, sName, attributes):
		if sName in ("Url", "os:Url"):
			if not attributes["type"] == "text/html":
				return
			self.element_content = attributes["template"]
			self.is_wanted_element = True
		else:
			xml_support.XMLEntryHandler.startElement(self, sName, attributes)

class GoogleSearch (Action):
	def __init__(self):
		Action.__init__(self, _("Search with Google"))

	def activate(self, leaf):
		from urllib import urlencode
		search_url = "http://www.google.com/search?"
		# will encode search=text, where `text` is escaped
		query_url = search_url + urlencode({"q": leaf.object, "ie": "utf-8"})
		utils.show_url(query_url)
	def get_description(self):
		return _("Search for this term with Google")
	def get_icon_name(self):
		return "gtk-find"
	def item_types(self):
		yield TextLeaf

def _urlencode(word):
	"""Urlencode a single string of bytes @word"""
	return urllib.urlencode({"q": word})[2:]

def _do_search_engine(terms, search_url, encoding="UTF-8"):
	search_url = search_url.encode(encoding, "strict")
	terms_enc = terms.encode(encoding, "ignore")
	query_url = search_url.replace("{searchTerms}", _urlencode(terms_enc))
	utils.show_url(query_url)

class SearchWithEngine (Action):
	def __init__(self):
		Action.__init__(self, _("Search with..."))

	def activate(self, leaf, iobj):
		coding = iobj.object.get("InputEncoding")
		url = iobj.object["Url"]
		_do_search_engine(leaf.object, url, encoding=coding)
		# will encode search=text, where `text` is escaped
		#query_url = search_url + urlencode({"q": leaf.object, "ie": "utf-8"})
		#utils.show_url(query_url)

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield SearchEngine

	def get_description(self):
		return _("Search the web with OpenSearch search engines")
	def get_icon_name(self):
		return "gtk-find"

class SearchEngine (Leaf):
	def get_description(self):
		desc = self.object.get("Url")
		return desc if desc != unicode(self) else None

class OpenSearchSource (Source):
	def __init__(self):
		Source.__init__(self, _("OpenSearch Search Engines"))

	@classmethod
	def _parse_opensearch(cls, filepaths):
		searches = []
		parser = xml.sax.make_parser()
		simplekeys = ["Description", "Url", "ShortName", "InputEncoding"]
		keys = simplekeys[:]
		keys += ["os:" + k for k in simplekeys]
		handler = OpenSearchHandler(searches, "SearchPlugin", {}, keys)
		parser.setContentHandler(handler)
		for filepath in filepaths:
			parser.parse(filepath)

		# normalize to unnamespaced values and sanitize
		for s in searches:
			for key, val in s.items():
				skey = key.replace("os:", "", 1)
				del s[key]
				s[skey] = val.strip()

		# remove those missing keys
		searches = [s for s in searches if all((k in s) for k in simplekeys)]
		return searches

	def get_items(self):
		plugin_dirs = []
		home_plugins = firefox_support.get_firefox_home_file("searchplugins")
		if home_plugins:
			plugin_dirs.append(home_plugins)
		# accept in kupfer data dirs
		plugin_dirs.extend(config.get_data_dirs("searchplugins"))

		for dirname, dirs, files in os.walk(home_plugins):
			break
		searches = self._parse_opensearch((os.path.join(dirname, f) for f in files))
		for s in searches:
			yield SearchEngine(s, s.get("ShortName"))

