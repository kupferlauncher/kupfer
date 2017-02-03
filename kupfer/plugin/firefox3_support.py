

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

	with open(bookmarks_file) as f:
		content = f.read().decode("UTF-8")
		# HACK: Firefox' JSON writer leaves a trailing comma
		# HACK: at the end of the array, which no parser accepts
		if content.endswith("}]},]}"):
			content = content[:-6] + "}]}]}"
		root = json_decoder(content)

	# make a dictionary of unique bookmarks
	bmap = {}

	def bmap_add(bmark, bmap):
		if bmark["id"] not in bmap:
			bmap[bmark["id"]] = bmark

	def bmap_add_tag(id_, tag, bmap):
		if not "tags" in bmap[id_]:
			bmap[id_]["tags"] = []
		else:
			print("Already in, gets tag:", tag)
		bmap[id_]["tags"].append(tag)

	MOZ_CONTAINER = "text/x-moz-place-container"
	MOZ_PLACE = "text/x-moz-place"
	UNWANTED_SCHEME = ("data", "place", "javascript")

	def is_container(ch):
		return ch["type"] == MOZ_CONTAINER
	def is_bookmark(ch):
		return ch["type"] == MOZ_PLACE and ch.get("uri")
	def is_good(ch):
		return not ch["uri"].split(":", 1)[0] in UNWANTED_SCHEME

	# find toplevel subfolders and tag folders
	catalogs = []
	tagcatalogs = []
	for child in root["children"]:
		if child.get("root") == "tagsFolder":
			tagcatalogs.extend(child["children"])
		elif child.get("root"):
			catalogs.append(child)

	# visit all subfolders recursively
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

	# visit all tag folders
	tags_catalogs = {}
	for tag in tagcatalogs:
		items = []
		for bmark in tag["children"]:
			if is_bookmark(bmark) and is_good(bmark):
				bmap_add(bmark, bmap)
				bmap_add_tag(bmark["id"], tag["title"], bmap)
				items.append(bmark)
		if items:
			tags_catalogs[tag['title']] = items

	return list(bmap.values()), tags_catalogs

if __name__ == '__main__':
	import os
	from . import firefox_support

	dirloc = firefox_support.get_firefox_home_file("bookmarkbackups")
	fpath = None
	if dirloc:
		files = os.listdir(dirloc)
		if files:
			latest_file = (files.sort() or files)[-1]
			fpath = os.path.join(dirloc, latest_file)

	if fpath and os.path.splitext(fpath)[-1].lower() == ".json":
		bookmarks, tags = get_bookmarks(fpath)
		print("Parsed # bookmarks:", len(bookmarks))
		print("Parsed # tags:", len(tags))
