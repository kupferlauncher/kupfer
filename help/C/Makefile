pages=$(wildcard *.page plugin/*.page)
htmls=$(patsubst %.page,%.html,$(pages))

all: $(htmls) index.cache

index.cache : $(pages)
	echo '<cache:cache xmlns:cache="http://projectmallard.org/cache/1.0/"' >$@.in
	echo '             xmlns="http://projectmallard.org/1.0/">'           >> $@.in
	for page in $(pages); do \
		echo "<page cache:href='$$page'/>" >> $@.in; \
	done
	echo '</cache:cache>' >> $@.in
	xsltproc `pkg-config --variable xsltdir gnome-doc-utils`/mallard/cache/mal-cache.xsl $@.in | xmllint --format - > $@
	rm $@.in

$(htmls) : index.cache
$(htmls) : %.html : %.page
	xsltproc \
	  --stringparam mal.cache.file `pwd`/index.cache \
	  --param mal.chunk.chunk_top 1 \
	  `pkg-config --variable mal2html gnome-doc-utils` $<

.PHONY: clean
clean:
	rm -fv index.cache *.html
