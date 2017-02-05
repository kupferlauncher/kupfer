# -*- coding: UTF-8 -*-



import os

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
        root = json_decoder(content)

    # make a dictionary of unique bookmarks
    bmap = {}

    def bmap_add(bmark, bmap):
        if bmark["id"] not in bmap:
            bmap[bmark["id"]] = bmark

    CONTAINER = "folder"
    UNWANTED_SCHEME = ("data", "place", "javascript")

    def is_container(ch):
        return ch["type"] == CONTAINER
    def is_bookmark(ch):
        return ch.get("url")
    def is_good(ch):
        return not ch["url"].split(":", 1)[0] in UNWANTED_SCHEME

    folders = []

    # add some folders
    folders.extend(root['roots']['bookmark_bar']['children'])
    folders.extend(root['roots']['other']['children'])

    for item in folders:
        if is_bookmark(item) and is_good(item):
            bmap_add(item, bmap)
        if is_container(item):
            folders.extend(item["children"])

    return list(bmap.values())

if __name__ == "__main__":
    fpath = os.path.expanduser("~/.config/chromium/Default/")
    print("Parsed # bookmarks:", len(list(get_bookmarks(fpath))))
