#  This makefile can generate html versions that are pleasant to read
#  needs python-docutils

all: Contributing.html Copyright.html Localization.html Manpage.html \
	Manual.html PluginAPI.html \
	GTKTheming.html VersionHistory.html

%.html: %.rst
	rst2html $^ > $@

%.pdf: %.rst
	rst2pdf -o $@ $^
