
def get_options(default_opts=""):
	"""
	Usage:
		-s, -S list     add list of sources
		-d dir, -D dir  add dir as dir source
		-r dir, -R dir  add dir as recursive dir source

		--depth d use recursive depth d

		--help          show usage help
		--debug         enable debug info

		small letter:   catalog item in catalog
		capital letter: direct inclusion, as well as catalog item

		list of sources:
		  a             applications
		  b             firefox bookmarks
		  c             recent documents
		  e             epiphany bookmarks
		  p             nautilus places
		  s				gnu screen sessions
		  w				windows
	
	The default is "-S acpsw -s e -D ~ -D ~/Desktop"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	opts = argv[1:]
	if "--debug" in opts:
		import debug
		opts.remove("--debug") 

	if len(opts) < 1:
		opts ="-S acpsw -s e -D ~ -D ~/Desktop".split()

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
	from . import objects, extensions
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

	sources = {
			"a": objects.AppSource(),
			"c": objects.RecentsSource(),
			"p": objects.PlacesSource(),
			"b": extensions.bookmarks.BookmarksSource(),
			"e": extensions.bookmarks.EpiphanySource(),
			"s": extensions.screen.ScreenSessionsSource(),
			"w": extensions.windows.WindowsSource(),
	}

	files = {
			"-d": dir_source,
			"-r": file_source,
	}

	for item in options.get("sources", ()):
		s_sources.append(sources[item])
	for item in options.get("include_sources", ()):
		S_sources.append(sources[item])
	
	for k, v in files.items():
		K = k.upper()
		if k in options:
			s_sources.extend(v(k))
		if K in options:
			S_sources.extend(v(K))

	if not S_sources and not s_sources:
		print "No sources"
		raise SystemExit(1)

	dc = data.DataController()
	dc.set_sources(S_sources, s_sources)
	w = browser.WindowController()
	w.main()

