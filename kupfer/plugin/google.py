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
		"SearchFor",
		"SearchWithEngine",
	)
__description__ = _("Search the web with OpenSearch search engines")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class OpenSearchHandler (xml_support.XMLEntryHandler):
	"""Parse OpenSearch specification files (Mozilla flavor)

	We use the generic entry parser from xml_support, but have
	to hack up a solution for the Url element, which _can_ be
	an entry itself with Param specifications.
	"""
	def __init__(self, entries, elem_name, attributes, keys):
		keys = set(keys)
		keys.update(("Param", "MozParam"))
		xml_support.XMLEntryHandler.__init__(self, entries, elem_name,
				attributes, keys)
		self.url_params = None

	def startElement(self, sName, attributes):
		if self.url_params is not None and sName == "Param":
			try:
				name, value = attributes["name"], attributes["value"]
			except AttributeError:
				return
			self.url_params.append((name, value))
		elif sName in ("Url", "os:Url"):
			if not attributes["type"] == "text/html":
				return
			self.element_content = attributes["template"]
			self.is_wanted_element = True
			self.url_params = []
		elif sName in ("MozParam", ):
			pass
		else:
			xml_support.XMLEntryHandler.startElement(self, sName, attributes)

	def endElement(self, sName):
		if self.url_params is not None and sName in ("Url", "os:Url"):
			# Assemble the URL with query string
			url = self.element_content.strip()
			if self.url_params:
				url += "?" + "&".join("%s=%s" % (n,v) for n,v in self.url_params)
			self.element_content = url
			self.url_params = None
		xml_support.XMLEntryHandler.endElement(self, sName)

def _urlencode(word):
	"""Urlencode a single string of bytes @word"""
	return urllib.urlencode({"q": word})[2:]

def _do_search_engine(terms, search_url, encoding="UTF-8"):
	"""Show an url searching for @search_url with @terms"""
	search_url = search_url.encode(encoding, "ignore")
	terms_enc = terms.encode(encoding, "ignore")
	query_url = search_url.replace("{searchTerms}", _urlencode(terms_enc))
	utils.show_url(query_url)

class SearchWithEngine (Action):
	"""TextLeaf -> SearchWithEngine -> SearchEngine"""
	def __init__(self):
		Action.__init__(self, _("Search With..."))

	def activate(self, leaf, iobj):
		coding = iobj.object.get("InputEncoding")
		url = iobj.object["Url"]
		_do_search_engine(leaf.object, url, encoding=coding)

	def item_types(self):
		yield TextLeaf

	def requires_object(self):
		return True
	def object_types(self):
		yield SearchEngine

	def object_source(self, for_item=None):
		return OpenSearchSource()

	def get_description(self):
		return _("Search the web with OpenSearch search engines")
	def get_icon_name(self):
		return "gtk-find"

class SearchFor (Action):
	"""SearchEngine -> SearchFor -> TextLeaf

	This is the opposite action to SearchWithEngine
	"""
	def __init__(self):
		Action.__init__(self, _("Search For..."))

	def activate(self, leaf, iobj):
		coding = leaf.object.get("InputEncoding")
		url = leaf.object["Url"]
		terms = iobj.object
		_do_search_engine(terms, url, encoding=coding)

	def item_types(self):
		yield SearchEngine

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf

	def get_description(self):
		return _("Search the web with OpenSearch search engines")
	def get_icon_name(self):
		return "gtk-find"

class SearchEngine (Leaf):
	def get_description(self):
		desc = self.object.get("Description")
		return desc if desc != unicode(self) else None
	def get_icon_name(self):
		return "text-html"

def coroutine(func):
	"""Coroutine decorator: Start the coroutine"""
	def startcr(*ar, **kw):
		cr = func(*ar, **kw)
		cr.next()
		return cr
	return startcr

class OpenSearchSource (Source):
	def __init__(self):
		Source.__init__(self, _("Search Engines"))

	@coroutine
	def _parse_opensearch(self, target):
		"""This is a coroutine to parse OpenSearch files"""
		parser = xml.sax.make_parser()
		reqkeys =  ["Description", "Url", "ShortName"]
		allkeys = reqkeys + ["InputEncoding"]
		keys = allkeys[:]
		keys += ["os:" + k for k in allkeys]
		searches = []
		handler = OpenSearchHandler(searches, "SearchPlugin", {}, keys)
		parser.setContentHandler(handler)
		while True:
			del searches[:]
			try:
				path = (yield)
				parser.parse(path)
			except xml.sax.SAXException, exc:
				self.output_debug("%s: %s" % (type(exc).__name__, exc))
			else:
				# normalize to unnamespaced values and sanitize
				for s in searches:
					for key, val in s.items():
						skey = key.replace("os:", "", 1)
						del s[key]
						s[skey] = val.strip()
					if all((k in s) for k in reqkeys):
						target.send(s)

	def get_items(self):
		plugin_dirs = []

		# accept in kupfer data dirs
		plugin_dirs.extend(config.get_data_dirs("searchplugins"))

		# firefox in home directory
		ffx_home = firefox_support.get_firefox_home_file("searchplugins")
		if ffx_home:
			plugin_dirs.append(ffx_home)

		plugin_dirs.extend(config.get_data_dirs("searchplugins",
			package="firefox"))
		plugin_dirs.extend(config.get_data_dirs("searchplugins",
			package="iceweasel"))

		self.output_debug("Found following searchplugins directories",
				sep="\n", *plugin_dirs)

		@coroutine
		def collect(seq):
			"""Collect items in list @seq"""
			while True:
				seq.append((yield))

		searches = []
		collector = collect(searches)
		parser = self._parse_opensearch(collector)
		# files are unique by filename to allow override
		visited_files = set()
		for pdir in plugin_dirs:
			for f in os.listdir(pdir):
				if f in visited_files:
					continue
				parser.send(os.path.join(pdir, f))
				visited_files.add(f)

		for s in searches:
			yield SearchEngine(s, s["ShortName"])

	def should_sort_lexically(self):
		return True

	def get_icon_name(self):
		return "applications-internet"
