#  This makefile is for convenience.
#
#  Run 'make' to build HTML documentation in the C directory
#  Run 'make $LANG' to update the translation file for language $LANG
#
#  To add a new language, edit Makefile.am

include Makefile.am


all:
	make -C C

$(DOC_LINGUAS): C/*.page
	xml2po -mmallard -u "$@/$@.po" C/*.page

