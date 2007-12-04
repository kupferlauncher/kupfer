#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
kupfer
ɹǝɟdnʞ
"""

def main():
	import sys
	from os import path

	import browser
	import objects

	print __doc__

	home = path.expanduser("~/")
	home_source = objects.DirectorySource(home)

	if len(sys.argv) < 2:
		dirs = []
	else:
		dirs = [path.abspath(p) for p in sys.argv[1:]]
	cmdline_source = objects.FileSource(dirs, depth=1)

	app_source = objects.AppSource()
	sources = (cmdline_source, home_source, app_source)
	sources_source = objects.SourcesSource(sources)

	sources = sources + (sources_source,)

	multi = objects.MultiSource(sources)
	w = browser.Browser(multi)
	w.main()

if __name__ == '__main__':
	main()
