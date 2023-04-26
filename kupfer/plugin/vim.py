#! /usr/bin/env python3
"""
Plugin generate recent opened files for vim/gvim.
"""
from __future__ import annotations

__kupfer_name__ = _("Vim")
__kupfer_sources__ = ("VimRecentsSource", "VimWikiSource")
__description__ = _("Load recent files edited in VIM/GVIM")
__version__ = "2023-04-02"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import typing as ty
from pathlib import Path
import time

from gi.repository import Gio

from kupfer import plugin_support, launch, icons
from kupfer.obj import FileLeaf, Source, SourceLeaf, Action
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.helplib import FilesystemWatchMixin

__kupfer_settings__ = plugin_support.PluginSettings(
    {
        "key": "wikis",
        "label": _("VimWiki directories:"),
        "type": list,
        "value": [],
        "helper": "choose_directory",
    },
    {
        "key": "limit",
        "label": _("Max recent documents:"),
        "type": int,
        "value": 25,
        "min": 1,
        "max": 100,
    },
)


def _load_recent_files(viminfo: Path, limit: int) -> ty.Iterable[FileLeaf]:
    with viminfo.open("rt", encoding="UTF-8", errors="replace") as fin:
        for line in fin:
            if not line.startswith("> "):
                continue

            *_dummy, filepath = line.strip().partition(" ")
            if filepath:
                yield FileLeaf(Path(filepath).expanduser())
                limit -= 1
                if not limit:
                    return


class VimRecentsSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = ("vim", "gvim")

    _viminfo_file = "~/.viminfo"

    def __init__(self, name=None):
        super().__init__(name=_("Vim Recent Documents"))
        self.monitor_token = None

    def initialize(self):
        viminfo = Path(self._viminfo_file).expanduser()
        self.monitor_token = self.monitor_files(viminfo)

    def finalize(self):
        self.stop_monitor_fs_changes(self.monitor_token)

    def monitor_include_file(self, gfile: Gio.File) -> bool:
        return bool(gfile)

    def get_items(self):
        viminfo = Path(self._viminfo_file).expanduser()
        if not viminfo.exists():
            self.output_debug("Viminfo not found at", viminfo)
            return
        limit = __kupfer_settings__["limit"]
        try:
            yield from _load_recent_files(viminfo, limit)
        except EnvironmentError:
            self.output_exc()
            return

    def get_icon_name(self):
        return "document-open-recent"

    def provides(self):
        yield FileLeaf


class VimWikiFile(FileLeaf):
    def __init__(self, path: Path, name: str) -> None:
        super().__init__(path, name)

    def get_actions(self):
        yield OpenVimWiki()


class VimWiki(SourceLeaf):
    def __init__(self, source: VimWikiFilesSource, name: str) -> None:
        super().__init__(source, name)

    def get_gicon(self):
        return icons.ComposedIconSmall("gvim", "emblem-documents")

    def get_description(self):
        return _("VimWiki in %s") % self.object.wikipath


class VimWikiSource(Source):
    def __init__(self):
        super().__init__(name=_("VimWiki Wikis"))

    def get_items(self):
        existing_wiki = []
        for path in __kupfer_settings__["wikis"] or ():
            filepath = Path(path).expanduser()
            if filepath.is_dir():
                name = filepath.name
                # make names unique (simple and not perfect)
                if name in existing_wiki:
                    name = f"{name} ({filepath.parent.name})"

                existing_wiki.append(name)
                yield VimWiki(VimWikiFilesSource(filepath), name)

    def provides(self):
        yield VimWiki

    def get_gicon(self):
        return icons.ComposedIconSmall("gvim", "emblem-documents")


class VimWikiFilesSource(Source):
    def __init__(self, wikipath: Path) -> None:
        super().__init__(wikipath.name)
        self.wikipath = wikipath
        self.update_ts = 0.0

    def repr_key(self) -> str:
        return str(self.wikipath)

    def is_dynamic(self) -> bool:
        # simple hack, cache only for 60 sec.
        # we can't monitor all directories / files, so better is keep cache
        # for some time
        return (time.monotonic() - self.update_ts) > 60

    def get_items(self) -> ty.Iterable[VimWikiFile]:
        self.update_ts = time.monotonic()
        # wiki can keep various files (txt, md, etc). Instead of read index
        # and guess extension - load add files in wiki
        wikipath = self.wikipath
        for dirname, dirs, files in os.walk(wikipath):
            dirp = Path(dirname)
            # skip hidden directories
            if dirp.name[0] == ".":
                dirs.clear()
                continue

            for file in files:
                # skip hidden files
                if file[0] == ".":
                    continue

                filepath = dirp.joinpath(file)
                yield VimWikiFile(filepath, str(filepath.relative_to(wikipath)))

    def provides(self):
        yield VimWikiFile

    def should_sort_lexically(self):
        return True


class OpenVimWiki(Action):
    rank_adjust = 20

    def __init__(self):
        super().__init__(name=_("Open in GVim"))

    def activate(self, leaf, iobj=None, ctx=None):
        launch.spawn_async(["gvim", leaf.object])

    def get_icon_name(self) -> str:
        return "gvim"
