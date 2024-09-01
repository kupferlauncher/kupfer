import json
import os
import typing as ty

_CONTAINER = "folder"
_UNWANTED_SCHEME = ("data", "place", "javascript")


def _is_container(item: dict[str, ty.Any]) -> bool:
    return item["type"] == _CONTAINER  # type:ignore


def _is_good_bookmark(item: dict[str, ty.Any]) -> bool:
    if url := item.get("url"):
        return url.split(":", 1)[0] not in _UNWANTED_SCHEME

    return False


def get_bookmarks(bookmarks_file: str) -> ty.Iterable[dict[str, ty.Any]]:
    # construct and configure the parser
    if not bookmarks_file:
        return

    with open(bookmarks_file, encoding="UTF-8") as fin:
        content = fin.read()
        root = json.loads(content)

    folders = []

    # add some folders
    folders.extend(root["roots"]["bookmark_bar"]["children"])
    folders.extend(root["roots"]["other"]["children"])

    # make a dictionary of unique bookmarks
    bmap = set()
    for item in folders:
        if _is_good_bookmark(item) and (iid := item["id"]) not in bmap:
            bmap.add(iid)
            yield item

        if _is_container(item):
            folders.extend(item["children"])


if __name__ == "__main__":
    fpath = os.path.expanduser("~/.config/chromium/Default/")
    print("Parsed # bookmarks:", len(list(get_bookmarks(fpath))))
