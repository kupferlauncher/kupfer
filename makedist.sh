#!/bin/sh

# I use this script to make the release tarballs
# It takes just a fresh clone of the repository, copies
# the waf binary in, and packages it up.
# Thus the dist ball is reasonably clean

set -x
set -e

OLDPWD=$PWD
TMPDIR="/tmp/$(basename $PWD)-dist"

test -e "$TMPDIR" && echo "$TMPDIR exists" && exit 2
echo Using $TMPDIR

git clone . "$TMPDIR"
cp waf "$TMPDIR"

cd "$TMPDIR"
./waf dist
cp -vi *.tar.gz "$OLDPWD"
rm -r "$TMPDIR"
