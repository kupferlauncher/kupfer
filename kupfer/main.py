_debug = False

try:
	import gettext
except ImportError:
	# Instally dummy identity function
	import __builtin__
	__builtin__._ = lambda x: x
else:
	package_name = "kupfer"
	localedir = "./locale"
	try:
		import version_subst
	except ImportError:
		pass
	else:
		package_name = version_subst.PACKAGE_NAME
		localedir = version_subst.LOCALEDIR
	gettext.install(package_name, localedir=localedir)

def get_options(default_opts=""):
	""" Usage:
	-s, -S list     add list of sources
	-d, -D dir      add dir as dir source
	-r, -R dir      add dir as recursive dir source

	--depth d use recursive depth d

	--help          show usage help
	--debug         enable debug info

	lowercase letter:   source as item in catalog
	uppercase letter:   items included directly

	list of sources:
	  a             applications
	  b             firefox bookmarks
	  c             recent documents
	  e             epiphany bookmarks
	  m             common items
	  p             nautilus places
	  s             gnu screen sessions
	  w             windows

	The default is "-S acmpsw -s e -D ~ -D ~/Desktop"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	opts = argv[1:]
	if "--debug" in opts:
		try:
			import debug
		except ImportError, e:
			print "%s" % e
		global _debug
		_debug = True
		opts.remove("--debug") 

	if len(opts) < 1:
		opts ="-S acmpsw -s e -D ~ -D ~/Desktop".split()

	try:
		opts, args = getopt(opts, "S:s:D:d:R:r:", ["depth=", "help"])
	except GetoptError, info:
		print info
		print get_options.__doc__
		raise SystemExit

	options = {}
	
	for k, v in opts:
		if k in ("-s", "-S"):
			if k == "-s":
				key = "sources"
			else:
				key = "include_sources"
			options.setdefault(key, []).extend(v)
		elif k in ("-d", "-D", "-r", "-R"):
			lst = options.get(k, [])
			lst.append(v)
			options[k] = lst
		elif k == "--depth":
			options["depth"] = v
		elif k == "--help":
			print get_options.__doc__
			raise SystemExit

	return options

def main():
	import sys
	from os import path

	from . import browser
	from . import objects, plugin
	from . import data

	options = get_options()

	s_sources = []
	S_sources = []
	default_depth = 1

	def dir_source(opt):
		for d in options[opt]:
			abs = path.abspath(path.expanduser(d))
			yield objects.DirectorySource(abs)

	def file_source(opt):
		depth = int(options.get("depth", default_depth))
		for d in options[opt]:
			abs = path.abspath(path.expanduser(d))
			yield objects.FileSource((abs,), depth)

	files = {
			"-d": dir_source,
			"-r": file_source,
	}

	sources = {
			"a": objects.AppSource(),
			"c": objects.RecentsSource(),
			"p": objects.PlacesSource(),
	}

	plugins = {
			"m": ("common", "CommonSource"),
			"b": ("bookmarks", "BookmarksSource"),
			"e": ("bookmarks", "EpiphanySource"),
			"s": ("screen", "ScreenSessionsSource"),
			"w": ("windows", "WindowsSource"),
	}

	def import_plugin(name):
		path = ".".join(["kupfer", "plugin", name])
		plugin = __import__(path, fromlist=(name,))
		return plugin

	def load_plugin_source(name, source_name):
		try:
			plugin = import_plugin(name)
		except ImportError, e:
			print "Skipping module %s: %s" % (name, e)
			return None
		else:
			source = getattr(plugin, source_name)
		return source()

	def get_source(key):
		if key in sources:
			yield sources[key]
		elif key in plugins:
			src = load_plugin_source(*plugins[key])
			if src:
				yield src
		else:
			print "No plugin for key:", key

	for item in options.get("sources", ()):
		s_sources.extend(get_source(item))
	for item in options.get("include_sources", ()):
		S_sources.extend(get_source(item))
	
	for k, v in files.items():
		K = k.upper()
		if k in options:
			s_sources.extend(v(k))
		if K in options:
			S_sources.extend(v(K))

	if not S_sources and not s_sources:
		print "No sources"
		raise SystemExit(1)

	if _debug:
		from . import pretty
		pretty.debug = _debug

	dc = data.DataController()
	dc.set_sources(S_sources, s_sources)
	w = browser.WindowController()
	w.main()

