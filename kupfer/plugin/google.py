import os
import urllib
import xml.etree.cElementTree as ElementTree

from kupfer.objects import Action, Source, Leaf
from kupfer.objects import TextLeaf
from kupfer import utils, config

from kupfer.plugin import firefox_support

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

def _noescape_urlencode(items):
	"""Assemble an url param string from @items, without
	using any url encoding.
	"""
	return "?" + "&".join("%s=%s" % (n,v) for n,v in items)

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

class OpenSearchParseError (StandardError):
	pass

class OpenSearchSource (Source):
	def __init__(self):
		Source.__init__(self, _("Search Engines"))

	@coroutine
	def _parse_opensearch(self, target):
		"""This is a coroutine to parse OpenSearch files"""
		vital_keys = set(["Url", "ShortName"])
		keys =  set(["Description", "Url", "ShortName", "InputEncoding"])
		mozns = '{http://www.mozilla.org/2006/browser/search/}'
		osns = '{http://a9.com/-/spec/opensearch/1.1/}'
		roots = ('OpenSearchDescription', 'SearchPlugin')
		gettagname = lambda tag: tag.rsplit("}", 1)[-1]

		def parse_etree(etree, name=None):
			if not gettagname(etree.getroot().tag) in roots:
				raise OpenSearchParseError("Search %s has wrong type" % name)
			search = {}
			for child in etree.getroot():
				tagname = gettagname(child.tag)
				if tagname not in keys:
					continue
				if (tagname == "Url" and child.get("type") == "text/html" and
						child.get("template")):
					text = child.get("template")
					params = {}
					for ch in child.getchildren():
						if gettagname(ch.tag) == "Param":
							params[ch.get("name")] = ch.get("value")
					if params:
						text += _noescape_urlencode(params.items())
				else:
					text = (child.text or "").strip()
				search[tagname] = text
			if not vital_keys.issubset(search.keys()):
				raise OpenSearchParseError("Search %s missing keys" % name)
			return search

		while True:
			try:
				path = (yield)
				etree = ElementTree.parse(path)
				target.send(parse_etree(etree, name=path))
			except StandardError, exc:
				self.output_debug("%s: %s" % (type(exc).__name__, exc))

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
