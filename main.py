#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Run Kupfer with some default arguments
"""

def print_intro():
	print """
WELCOME TO

kupfer
ɹǝɟdnʞ
"""

def main():
	print_intro()
	import sys
	from os import path

	import browser
	import objects
	home = path.expanduser("~/")
	print home
	home_source = objects.DirectorySource(home)

	if len(sys.argv) < 2:
		dirs = []
	else:
		dirs = sys.argv[1:]
	cmdline_source = objects.FileSource(dirs, depth=1)

	app_source = objects.AppSource()
	#sources_source = objects.SourcesSource((home_source, app_source))

	sources = (cmdline_source, home_source, app_source)
	multi = objects.MultiSource(sources)
	w = browser.Browser(multi)
	w.main()

if __name__ == '__main__':
	main()
