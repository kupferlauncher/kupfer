from __future__ import with_statement

try:
	import cjson
	json_decoder = cjson.decode
except ImportError:
	import json
	json_decoder = json.loads

def get_bookmarks(bookmarks_file):
	# construct and configure the parser
	if not bookmarks_file:
		return []

	bmap = {}

	def bmap_add(bmark, bmap):
		if bmark["id"] not in bmap:
			bmap[bmark["id"]] = bmark

	def bmap_add_tag(id_, tag, bmap):
		if not "tags" in bmap[id_]:
			bmap[id_]["tags"] = []
		else:
			print "Already in, gets tag:", tag
		bmap[id_]["tags"].append(tag)

	with open(bookmarks_file) as f:
		content = f.read().decode("UTF-8")
		root = json_decoder(content)

	catalogs = []
	tagcatalogs = []
	for child in root["children"]:
		if child.get("root") == "tagsFolder":
			tagcatalogs.extend(child["children"])
		elif child.get("root"):
			catalogs.append(child)

	MOZ_CONTAINER = "text/x-moz-place-container"
	MOZ_PLACE = "text/x-moz-place"
	UNWANTED_SCHEME = ("data", "place", "javascript")
	is_container = lambda ch: ch["type"] == MOZ_CONTAINER
	is_bookmark = lambda ch: ch["type"] == MOZ_PLACE and ch.get("uri")
	is_good = lambda ch: not ch["uri"].split(":", 1)[0] in UNWANTED_SCHEME

	visited = set()
	while catalogs:
		next = catalogs.pop()
		if next["id"] in visited:
			continue
		for child in next["children"]:
			if is_container(child):
				catalogs.append(child)
				tagcatalogs.append(child)
			elif is_bookmark(child) and is_good(child):
				bmap_add(child, bmap)
		visited.add(next["id"])

	for tag in tagcatalogs:
		for bmark in tag["children"]:
			if is_bookmark(bmark) and is_good(bmark):
				bmap_add(bmark, bmap)
				bmap_add_tag(bmark["id"], tag["title"], bmap)
	bookmarks = []
	for b in bmap.values():
		if not b.get("uri"):
			print "Has no uri:", b
		else:
			bookmarks.append(b)
	return bookmarks
