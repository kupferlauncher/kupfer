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
	if len(sys.argv) < 2:
		dir = "."
	else:
		dir = sys.argv[1]
	dir = path.abspath(dir)
	dir_source = objects.DirectorySource(dir)
	file_source = objects.FileSource(sys.argv[1:], depth=2)
	app_source = objects.AppSource()
	source = objects.SourcesSource((dir_source, file_source, app_source))
	w = browser.Browser(source)
	w.main()

if __name__ == '__main__':
	main()
