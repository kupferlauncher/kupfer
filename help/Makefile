#  This makefile is for convenience.
#
#  Run 'make' to build HTML documentation in the C directory
#  Run 'make $LANG' to update the translation file for language $LANG
#
#  To add a new language, edit Makefile.am

include Makefile.am

C:
	make -C C


$(DOC_LINGUAS): C/*.page
	xml2po -mmallard -u "$@/$@.po" C/*.page


html:
	for lang in C $(DOC_LINGUAS) ; do \
		rm -r $$lang ; \
		mkdir $$lang ; \
		yelp-build html -o $$lang /usr/share/help/$$lang/kupfer ; \
	done
