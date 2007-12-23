#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
kupfer
ɹǝɟdnʞ

Copyright 2007 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
USA
"""

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
		capital letter: direct inclusion

		list of sources:
		  a             applications
		  b             firefox bookmarks
		  c             recent documents
		  e             epiphany bookmarks
		  p             nautilus places
	
	The default is "-S ap -s aecp -D ~"
	"""
	from getopt import getopt, GetoptError
	from sys import argv

	opts = argv[1:]
	if "--debug" in opts:
		import debug
		opts.remove("--debug") 

	if len(opts) < 1:
		opts ="-S ap -s aecp -D ~".split()

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
		depth = int(options.get("depth", default_depth))
		for d in options[opt]:
			abs = path.abspath(path.expanduser(d))
			yield objects.FileSource((abs,), depth)

	sources = {
			"a": objects.AppSource(),
			"b": objects.BookmarksSource(),
			"c": objects.RecentsSource(),
			"e": objects.EpiphanySource(),
			"p": objects.PlacesSource(),
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

	if len(s_sources):
		S_sources.append(objects.SourcesSource(s_sources))
	
	if len(S_sources) == 1:
		root_catalog, = S_sources
	elif len(S_sources) > 1:
		root_catalog = objects.MultiSource(S_sources)
	else:
		print "No sources"
		raise SystemExit(1)

	w = browser.WindowController(root_catalog)
	w.main()

if __name__ == '__main__':
	main()
