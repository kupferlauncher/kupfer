#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
kupfer
ɹǝɟdnʞ
"""

def get_options(default_opts=""):
	"""
	Usage:
		-a, -A          search applications
		-b, -B          firefox bookmarks
		-c, -C          recent documents
		-d dir, -D dir  add dir as dir source
		-r dir, -R dir  add dir as recursive dir source
		--depth d use recursive depth d

		small letter:   catalog item in catalog
		capital letter: direct inclusion
	
	The default is "-AabCc -D ~"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	if len(argv) > 1:
		opts = argv[1:]
	else:
		opts ="-AabCc -D ~".split()

	try:
		opts, args = getopt(opts, "AaBbCcD:d:R:r:", "depth=")
	except GetoptError, info:
		print info
		print get_options.__doc__
		raise SystemExit

	options = {}
	
	for k, v in opts:
		if k in ("-a", "-A", "-b", "-B", "-c", "-C"):
			options[k] = True
		elif k in ("-d", "-D", "-r", "-R"):
			lst = options.get(k, [])
			lst.append(v)
			options[k] = lst
		elif k == "--depth":
			options["depth"] = v
	
	return options


def main():
	import sys
	from os import path

	import browser
	import objects

	print __doc__

	options = get_options()
	
	s_sources = []
	S_sources = []
	default_depth = 1

	def dir_source(opt):
		for d in options[opt]:
			abs = path.abspath(path.expanduser(d))
			yield objects.DirectorySource(abs)

	def file_source(opt):
		depth = options.get("depth", default_depth)
		def abs_paths():
			for d in options[opt]:
				abs = path.abspath(path.expanduser(d))
				yield abs
		yield objects.FileSource(tuple(abs_paths()), depth)

	sources = {
			"-b":  objects.BookmarksSource(),
			"-a":  objects.AppSource(), 
			"-c":  objects.RecentsSource()
	}

	files = {
			"-d": dir_source,
			"-r": file_source,
	}

	for k, v in sources.items():
		K = k.upper()
		if k in options:
			s_sources.append(v)
		if K in options:
			S_sources.append(v)
	
	for k, v in files.items():
		K = k.upper()
		if k in options:
			s_sources.extend(v(k))
		if K in options:
			S_sources.extend(v(K))

	if len(s_sources):
		S_sources.append(objects.SourcesSource(s_sources))
	
	if len(S_sources) == 1:
		root, = S_sources
	elif len(S_sources) > 1:
		root = objects.MultiSource(S_sources)
	else:
		print "No sources"
		raise SystemExit

	w = browser.Browser(root)
	w.main()

if __name__ == '__main__':
	main()
