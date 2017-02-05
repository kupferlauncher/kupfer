"""
Parse Epiphany's bookmarks file
Inspired by the Epiphany handler from the deskbar project
"""

__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


import xml.etree.cElementTree as ElementTree

EPHY_BOOKMARKS_FILE = "~/.gnome2/epiphany/bookmarks.rdf"

def parse_epiphany_bookmarks(filename):
    """
    Yield a sequence of bookmarks
    """
    UNWANTED_SCHEME = set(("data", "javascript"))

    ns = "{http://purl.org/rss/1.0/}"
    ITEM_NAME = ns + "item"
    HREF_NAME = ns + "link"
    TITLE_NAME = ns + "title"

    def get_item(entry):
        """Return a bookmarks item or None if not good"""
        title, href = None, None
        for child in entry.getchildren():
            if child.tag == HREF_NAME:
                href = child.text
                if not href or href.split(":", 1)[0].lower() in UNWANTED_SCHEME:
                    return None
            if child.tag == TITLE_NAME:
                title = child.text
        return title and href and (title, href)

    for event, entry in ElementTree.iterparse(filename):
        if entry.tag != ITEM_NAME:
            continue
        item = get_item(entry)
        if item:
            yield item

if __name__ == '__main__':
    import os
    f = os.path.expanduser(EPHY_BOOKMARKS_FILE)
    print("Got ET # bookmarks:", len(list(parse_epiphany_bookmarks(f))))
