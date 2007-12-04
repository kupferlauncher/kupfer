#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
kupfer
ɹǝɟdnʞ
"""

def get_options():
	"""
	Usage:
		-a        search applications
		-d dir    add dir as dir source
		-r dir    add dir as recursive dir source
		--depth d use recursive depth d
	
	Without options, the equivalent is "-a -d ~"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	try:
		opts, args = getopt(argv[1:], "ad:r:", "depth=")
	except GetoptError, info:
		print info
		print get_options.__doc__
		raise SystemExit

	options = {}
	
	for k, v in opts:
		if k == "-a":
			options["applications"] = True
		elif k == "-d":
			lst = options.get("dirs", [])
			lst.append(v)
			options["dirs"] = lst
		elif k == "-r":
			lst = options.get("recurs", [])
			lst.append(v)
			options["recurs"] = lst
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
	if not len(options):
		home = path.expanduser("~/")
		home_source = objects.DirectorySource(home)
		app_source = objects.AppSource()
		sources_source = objects.SourcesSource((app_source,))
		sources = (home_source, app_source, sources_source)
	else:
		sources = []
		if "dirs" in options:
			for d in options["dirs"]:
				abs = path.abspath(d)
				sources.append(objects.DirectorySource(abs))
		if "recurs" in options:
			depth = options.get("depth", 1)
			for d in options["recurs"]:
				abs = path.abspath(d)
				sources.append(objects.FileSource(abs, depth))
		if "applications" in options:
			app_source = objects.AppSource()
			sources.append(app_source)
			if len(sources) > 1:
				sources.append(object.SourcesSource(app_source))
	
	hist = {}
	for s in sources:
		hist[str(s)] = hist.get(str(s), 0) + 1
	
	print "\n".join("%s   %s" % (s,hist[s] ) for s in hist)

	multi = objects.MultiSource(sources)
	w = browser.Browser(multi)
	w.main()

if __name__ == '__main__':
	main()
