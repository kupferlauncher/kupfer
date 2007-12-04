#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
kupfer
ɹǝɟdnʞ
"""

def get_options():
	"""
	Usage:
		-a, -A          search applications
		-b, -B          firefox bookmarks
		-d dir, -D dir  add dir as dir source
		-r dir, -R dir  add dir as recursive dir source
		-c, -C          recent documents
		--depth d use recursive depth d

		small letter:   catalog item in catalog
		capital letter: direct inclusion
	
	Without options, the equivalent is "-aAb -d ~"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	try:
		opts, args = getopt(argv[1:], "AaBbCcd:r:", "depth=")
	except GetoptError, info:
		print info
		print get_options.__doc__
		raise SystemExit

	options = {}
	
	for k, v in opts:
		if k == "-a":
			options["applications"] = True
		elif k == "-A":
			options["applications_inline"] = True
		elif k == "-b":
			options["bookmarks"] = True
		elif k == "-B":
			options["bookmarks_inline"] = True
		elif k == "-c":
			options["recents"] = True
		elif k == "-C":
			options["recents_inline"] = True
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
		options = { "dirs": [path.expanduser("~/"),],
				"applications":"", "applications_inline":"",
				"bookmarks":"" }
	
	sources = []
	ss_sources = []
	bookmarks = objects.BookmarksSource()
	apps = objects.AppSource()
	recents = objects.RecentsSource()

	if "dirs" in options:
		for d in options["dirs"]:
			abs = path.abspath(path.expanduser(d))
			sources.append(objects.DirectorySource(abs))
	if "recurs" in options:
		depth = options.get("depth", 1)
		abs = [path.abspath(d) for d in options["recurs"]]
		sources.append(objects.FileSource(abs, depth))
	if "bookmarks" in options:
		ss_sources.append(bookmarks)
	if "bookmarks_inline" in options:
		sources.append(bookmarks)
	if "applications" in options:
		ss_sources.append(apps)
	if "applications_inline" in options:
		sources.append(apps)
	if "recents" in options:
		ss_sources.append(recents)
	if "recents_inline" in options:
		sources.append(recents)

	if len(ss_sources):
		sources.append(objects.SourcesSource(ss_sources))
	
	hist = {}
	for s in sources:
		hist[str(s)] = hist.get(str(s), 0) + 1
	
	print "\n".join("%s   %s" % (s,hist[s] ) for s in hist)

	if len(sources) == 1:
		root, = sources
	elif len(sources) > 1:
		root = objects.MultiSource(sources)
	else:
		print "No sources"
		raise SystemExit

	w = browser.Browser(root)
	w.main()

if __name__ == '__main__':
	main()
